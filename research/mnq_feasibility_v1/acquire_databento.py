"""Fixed, user-approved MNQU6 pilot. Submit once; collect existing jobs safely."""
import base64
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from quote_databento import DAYS, ROOT, NoRedirect, load_key, metadata

DEST = ROOT / 'research/mnq_feasibility_v1/data/databento-pilot-20260908'
CAP = Decimal('12')
BASE = 'https://hist.databento.com/v0/'
ENDPOINTS = {'batch.submit_job': 'POST', 'batch.get_job_details': 'GET',
             'batch.list_files': 'GET', 'symbology.resolve': 'POST'}


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, obj):
    # Exclusive, flushed files make an interrupted submission visible on restart.
    with path.open('x') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def headers(key):
    return {'Authorization': 'Basic ' + base64.b64encode((key + ':').encode()).decode()}


def api(endpoint, params, key):
    method = ENDPOINTS[endpoint]
    encoded = urlencode(params).encode()
    url = BASE + endpoint
    if method == 'GET':
        url += '?' + encoded.decode()
    req = Request(url, data=encoded if method == 'POST' else None, headers=headers(key), method=method)
    with build_opener(NoRedirect()).open(req, timeout=60) as response:
        return json.loads(response.read())


def plan():
    ranges = [('mbp-1', d + 'T13:30:00Z', d + 'T20:00:00Z') for d in DAYS]
    ranges += [('definition', '2026-08-31T00:00:00Z', '2026-09-05T00:00:00Z')]
    return [dict(dataset='GLBX.MDP3', symbols='MNQU6', stype_in='raw_symbol',
                 schema=s, start=a, end=b) for s, a, b in ranges]


def clean_job(job):
    return {k: v for k, v in job.items() if k not in ('api_key', 'user_id')}


def validate_costs(costs):
    if len(costs) != 6 or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in costs):
        raise ValueError('Invalid quotes')
    values = [Decimal(str(c)) for c in costs]
    if any(not c.is_finite() or c <= 0 for c in values) or sum(values) >= CAP:
        raise ValueError('Estimate outside approved scope')
    return sum(values)


def submit(key):
    # Never recreate an acquisition directory or silently retry a paid submission.
    DEST.mkdir(parents=True, exist_ok=False)
    requests = plan()
    costs = [metadata('metadata.get_cost', p, key) for p in requests]
    total = validate_costs(costs)
    save(DEST / 'approval-and-quote.json', dict(at=now(), user_approved=True,
         estimated_total_usd=str(total), estimate_ceiling_usd=str(CAP),
         actual_billing_is_delivery_based=True,
         requests=[dict(request=p, estimated_usd=str(c)) for p, c in zip(requests, costs)]))
    print('Refreshed estimate USD:', total, '(below approved $12)', flush=True)
    mapping = api('symbology.resolve', dict(dataset='GLBX.MDP3', symbols='MNQU6',
         stype_in='raw_symbol', stype_out='instrument_id', start_date=DAYS[0], end_date='2026-09-05'), key)
    save(DEST / 'symbology-resolution.json', mapping)
    resolved = mapping.get('result', {}).get('MNQU6', [])
    if mapping.get('not_found') or mapping.get('partial') or not resolved:
        raise ValueError('Incomplete symbol resolution')
    print('Exact contract symbol resolved.', flush=True)
    for i, params in enumerate(requests):
        jobdir = DEST / ('request-%02d' % i)
        jobdir.mkdir()
        payload = dict(params, encoding='dbn', compression='zstd', delivery='download',
                       split_duration='day', stype_out='instrument_id')
        save(jobdir / 'submission-intent.json', dict(at=now(), request=payload))
        # An uncertain HTTP response must be reconciled via job history, never retried here.
        job = api('batch.submit_job', payload, key)
        save(jobdir / 'submitted.json', clean_job(job))
        print('Submitted', i, job['id'], job.get('state'), flush=True)


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def download(jobdir, item, key):
    name = item['filename']
    if not name or Path(name).name != name or name in ('.', '..'):
        raise ValueError('Unsafe download filename')
    expected = item['hash'].removeprefix('sha256:')
    if not re.fullmatch('[a-fA-F0-9]{64}', expected):
        raise ValueError('Missing SHA256')
    folder = jobdir / 'files'
    folder.mkdir(exist_ok=True)
    target = folder / name
    if target.exists():
        if target.stat().st_size == item['size'] and sha256(target) == expected:
            return dict(filename=name, bytes=item['size'], sha256=expected)
        raise ValueError('Existing file failed integrity check')
    url = item['urls']['https']
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname not in ('hist.databento.com', 'api.databento.com') or parts.username or parts.port not in (None, 443):
        raise ValueError('Unexpected download origin; no credentials sent')
    temporary = target.with_name(target.name + '.partial')
    # Redownloads of an existing batch do not submit another paid request.
    with build_opener(NoRedirect()).open(Request(url, headers=headers(key)), timeout=60) as response, temporary.open('wb') as stream:
        for block in iter(lambda: response.read(1024 * 1024), b''):
            stream.write(block)
    if temporary.stat().st_size != item['size'] or sha256(temporary) != expected:
        raise ValueError('Downloaded file failed integrity check')
    temporary.rename(target)
    print('Verified', name, item['size'], 'bytes', flush=True)
    return dict(filename=name, bytes=item['size'], sha256=expected)


def collect(key):
    completed = []
    pending = []
    for i in range(6):
        folder = DEST / ('request-%02d' % i)
        job = json.loads((folder / 'submitted.json').read_text())
        details = clean_job(api('batch.get_job_details', {'job_id': job['id']}, key))
        if details.get('state') != 'done':
            pending.append(dict(id=job['id'], state=details.get('state')))
            continue
        if not (folder / 'completed-job.json').exists():
            save(folder / 'completed-job.json', details)
        listing = api('batch.list_files', {'job_id': job['id']}, key)
        if not listing or not any(f['filename'].endswith('.dbn.zst') for f in listing):
            raise ValueError('No DBN file in completed job')
        if not (folder / 'file-list.json').exists():
            save(folder / 'file-list.json', [{k: v for k, v in f.items() if k != 'urls'} for f in listing])
        verified = [download(folder, f, key) for f in listing]
        completed.append(dict(request_index=i, job=details, files=verified))
    if pending:
        print('Pending jobs:', json.dumps(pending), flush=True)
        return
    summary = dict(at=now(), status='DOWNLOADED_HASH_VERIFIED_NOT_REPLAY_VALIDATED',
        requests=completed, file_count=sum(len(x['files']) for x in completed),
        total_bytes=sum(f['bytes'] for x in completed for f in x['files']),
        provider_cost_usd=str(sum(Decimal(str(x['job']['cost_usd'])) for x in completed))
            if all(x['job'].get('cost_usd') is not None for x in completed) else None,
        note='File transport integrity verified. Market-data quality and strategy performance are not yet validated.')
    if not (DEST / 'download-summary.json').exists():
        save(DEST / 'download-summary.json', summary)
    print('COMPLETE:', json.dumps({k: v for k, v in summary.items() if k != 'requests'}), flush=True)


if __name__ == '__main__':
    try:
        mode = sys.argv[1] if len(sys.argv) == 2 else ''
        if mode not in ('submit', 'collect'):
            raise ValueError('Choose submit or collect')
        {'submit': submit, 'collect': collect}[mode](load_key())
    except HTTPError as error:
        print('Stopped: HTTP', error.code, '(response suppressed; do not retry submissions)', file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print('Stopped:', type(error).__name__, '(details suppressed; inspect saved state before resuming)', file=sys.stderr)
        sys.exit(1)
