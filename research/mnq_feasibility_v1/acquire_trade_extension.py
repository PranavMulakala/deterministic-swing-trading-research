"""Fixed approved trades-first extension. No brokerage, no live subscriptions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
import json
import sys
from urllib.error import HTTPError

from acquire_databento import api, clean_job, download, now, save
from quote_databento import ROOT, load_key, metadata

DEST = ROOT / 'research/mnq_feasibility_v1/data/databento-trade-extension-v1'
STAGE_CAP = Decimal('22')
TOTAL_CAP = Decimal('56')


def plan():
    first = date(2026, 8, 3)
    days = [(first + timedelta(days=n)).isoformat() for n in range(26)
            if (first + timedelta(days=n)).weekday() < 5]
    return [dict(dataset='GLBX.MDP3', symbols='MNQU6', stype_in='raw_symbol',
                 schema='trades', start=d+'T13:30:00Z', end=d+'T20:00:00Z')
            for d in days] + [dict(dataset='GLBX.MDP3', symbols='MNQU6',
                 stype_in='raw_symbol', schema='definition',
                 start='2026-08-03T00:00:00Z', end='2026-08-29T00:00:00Z')]


def validate_costs(costs):
    if len(costs) != 21 or any(type(c) not in (float, int) for c in costs):
        raise ValueError('Invalid cost response')
    values = [Decimal(str(c)) for c in costs]
    if any(not c.is_finite() or c < 0 for c in values):
        raise ValueError('Invalid cost response')
    total = sum(values)
    if not 0 < total < STAGE_CAP or total >= TOTAL_CAP:
        raise ValueError('Estimate outside approved stage')
    return total


def submit(key):
    DEST.mkdir(parents=True, exist_ok=False)
    requests = plan()
    with ThreadPoolExecutor(max_workers=4) as pool:
        costs = list(pool.map(lambda p: metadata('metadata.get_cost', p, key), requests))
    total = validate_costs(costs)
    save(DEST/'approval-and-quote.json', dict(at=now(), stage='TRADES_FIRST',
        user_approved_research_only=True, estimated_total_usd=str(total),
        stage_estimate_ceiling_usd=str(STAGE_CAP), extension_estimate_ceiling_usd=str(TOTAL_CAP),
        actual_billing_is_delivery_based=True, portal_limit_not_changed=True,
        requests=[dict(request=p, estimated_usd=str(c)) for p,c in zip(requests,costs)]))
    mapping = api('symbology.resolve', dict(dataset='GLBX.MDP3', symbols='MNQU6',
        stype_in='raw_symbol', stype_out='instrument_id',
        start_date='2026-08-03', end_date='2026-08-29'), key)
    save(DEST/'symbology-resolution.json', mapping)
    rows = mapping.get('result', {}).get('MNQU6', [])
    if mapping.get('not_found') or mapping.get('partial') or not rows:
        raise ValueError('Incomplete symbol resolution')
    if any(str(r.get('s')) != '42004800' for r in rows):
        raise ValueError('Unexpected instrument resolution')
    print('Refreshed stage estimate USD:', total, '(below $22; approved extension $56)', flush=True)
    for i, params in enumerate(requests):
        folder = DEST/('request-%02d' % i)
        folder.mkdir()
        payload = dict(params, encoding='dbn', compression='zstd', delivery='download',
            split_duration='day', stype_out='instrument_id')
        save(folder/'submission-intent.json', dict(at=now(), request=payload))
        job = api('batch.submit_job', payload, key)
        save(folder/'submitted.json', clean_job(job))
        print('Submitted', i, job['id'], job.get('state'), flush=True)


def collect(key):
    if not (DEST/'approval-and-quote.json').exists():
        raise ValueError('Missing acquisition approval journal')
    completed, pending = [], []
    for i, request in enumerate(plan()):
        folder = DEST/('request-%02d' % i)
        if not (folder/'submitted.json').exists():
            pending.append(dict(request_index=i, state='NOT_SUBMITTED_OR_UNCERTAIN_REQUIRES_RECONCILIATION'))
            continue
        job = json.loads((folder/'submitted.json').read_text())
        details = clean_job(api('batch.get_job_details', dict(job_id=job['id']), key))
        if details.get('state') != 'done':
            pending.append(dict(id=job['id'], state=details.get('state')))
            continue
        if not (folder/'completed-job.json').exists():
            save(folder/'completed-job.json', details)
        listing = api('batch.list_files', dict(job_id=job['id']), key)
        if not listing or not any(f['filename'].endswith('.dbn.zst') for f in listing):
            raise ValueError('No DBN data in completed job')
        if not (folder/'file-list.json').exists():
            save(folder/'file-list.json', [{k:v for k,v in f.items() if k!='urls'} for f in listing])
        verified = [download(folder, f, key) for f in listing]
        completed.append(dict(request_index=i, job=details, files=verified))
    if pending:
        print('Pending:', json.dumps(pending), flush=True)
        return
    costs = [Decimal(str(x['job']['cost_usd'])) for x in completed]
    if any(not c.is_finite() or c < 0 for c in costs):
        raise ValueError('Unknown usage; block next stage')
    summary = dict(at=now(), status='DOWNLOADED_HASH_VERIFIED_NOT_REPLAY_VALIDATED',
        requests=completed, file_count=sum(len(x['files']) for x in completed),
        total_bytes=sum(f['bytes'] for x in completed for f in x['files']),
        provider_cost_usd=str(sum(costs)), remaining_extension_budget_usd=str(TOTAL_CAP-sum(costs)),
        note='Credits/card settlement not checked. No quote execution or strategy profitability established.')
    if not (DEST/'download-summary.json').exists():
        save(DEST/'download-summary.json', summary)
    print('COMPLETE:', json.dumps({k:v for k,v in summary.items() if k!='requests'}), flush=True)


if __name__ == '__main__':
    try:
        mode = sys.argv[1] if len(sys.argv)==2 else ''
        if mode not in ('submit', 'collect'):
            raise ValueError('Choose submit or collect')
        {'submit':submit, 'collect':collect}[mode](load_key())
    except HTTPError as error:
        print('Stopped: HTTP', error.code, '(details suppressed; do not retry submissions)', file=sys.stderr)
        raise SystemExit(1)
    except Exception as error:
        print('Stopped:', type(error).__name__, '(details suppressed; inspect saved state)', file=sys.stderr)
        raise SystemExit(1)
