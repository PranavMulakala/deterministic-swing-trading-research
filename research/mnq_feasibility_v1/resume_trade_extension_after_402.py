"""One-use recovery of the confirmed HTTP402 rejection after user's limit update.

This is not generic retry logic. Unknown responses always require reconciliation.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from urllib.error import HTTPError

from acquire_trade_extension import DEST, STAGE_CAP, TOTAL_CAP, plan
from acquire_databento import api, clean_job, now, save
from quote_databento import load_key, metadata
from reconcile_trade_extension import fetch_jobs
from validate_download import ns


def main():
    approval=json.loads((DEST/'approval-and-quote.json').read_text())
    requests=plan()
    # Preserve the exact interrupted prefix and prevent automatic repeat recovery.
    if not (DEST/'request-13/submission-intent.json').exists():
        raise ValueError('Expected HTTP402 interruption journal missing')
    journal=DEST/'resume-after-confirmed-402'
    journal.mkdir(exist_ok=False)
    key=load_key()
    jobs=fetch_jobs(key,approval['at'])
    accepted=[]
    for i,wanted in enumerate(requests):
        matches=[j for j in jobs if all(j.get(f)==wanted[f] for f in ('dataset','symbols','stype_in','schema'))
            and ns(j['start'])==ns(wanted['start']) and ns(j['end'])==ns(wanted['end'])]
        known=DEST/('request-%02d'%i)/'submitted.json'
        if i<13:
            if len(matches)!=1 or not known.exists() or matches[0]['id']!=json.loads(known.read_text())['id'] or matches[0]['state']!='done':
                raise ValueError('Accepted prefix requires reconciliation')
            accepted.append(matches[0])
        elif matches or known.exists():
            raise ValueError('Missing request already has a provider/local job; do not resubmit')
    used=[Decimal(str(j['cost_usd'])) for j in accepted]
    if any(not c.is_finite() or c<0 for c in used):raise ValueError('Invalid prior billed cost')
    pending=requests[13:]
    with ThreadPoolExecutor(max_workers=4) as pool:
        costs=list(pool.map(lambda p:metadata('metadata.get_cost',p,key),pending))
    if len(costs)!=8 or any(type(c) not in (int,float) for c in costs):raise ValueError('Invalid remaining estimates')
    estimated=[Decimal(str(c)) for c in costs]
    if any(not c.is_finite() or c<0 for c in estimated):raise ValueError('Invalid remaining estimates')
    combined=sum(used)+sum(estimated)
    if not 0<combined<STAGE_CAP or combined>=TOTAL_CAP:raise ValueError('Stage budget would be exceeded')
    save(journal/'reconciliation-and-quote.json',dict(at=now(),
        prior_rejection='HTTP402 on request13 observed in original submission tool output',
        user_update='User reports monthly limit raised to $75; only use as needed. Original $56 research scope retained.',
        confirmed_accepted_ids=[j['id'] for j in accepted],
        provider_cost_to_date_usd=str(sum(used)),remaining_estimated_usd=str(sum(estimated)),
        combined_stage_estimated_usd=str(combined),
        missing_requests_confirmed_against_provider_history=True,
        requests=[dict(request=p,estimated_usd=str(c)) for p,c in zip(pending,estimated)]))
    print('Prior usage:',sum(used),'remaining estimate:',sum(estimated),'combined stage:',combined,flush=True)
    for i in range(13,21):
        folder=DEST/('request-%02d'%i)
        folder.mkdir(exist_ok=True)
        payload=dict(requests[i],encoding='dbn',compression='zstd',delivery='download',
            split_duration='day',stype_out='instrument_id')
        save(folder/'resume-submission-intent.json',dict(at=now(),request=payload))
        try:
            job=api('batch.submit_job',payload,key)
        except HTTPError as error:
            save(journal/'http-error.json',dict(at=now(),request_index=i,http_status=error.code,
                resubmission_allowed=False,note='Reconcile before any new attempt.'))
            raise
        save(folder/'submitted.json',clean_job(job))
        print('Submitted missing request',i,job['id'],job.get('state'),flush=True)


if __name__=='__main__':
    try:main()
    except HTTPError as error:
        print('Recovery stopped: HTTP',error.code,'(details suppressed; no retry)');raise SystemExit(1)
    except Exception as error:
        print('Recovery stopped:',type(error).__name__,'(details suppressed; no retry)');raise SystemExit(1)
