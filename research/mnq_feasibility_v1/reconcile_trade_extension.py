"""Read-only job reconciliation; cannot submit, purchase, or change billing."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError

from acquire_trade_extension import DEST, plan
from acquire_databento import headers, save
from quote_databento import NoRedirect, load_key
from validate_download import ns


def fetch_jobs(key, since):
    query=urlencode(dict(since=since,states='queued,processing,done,expired',short='false'))
    request=Request('https://hist.databento.com/v0/batch.list_jobs?'+query,headers=headers(key))
    with build_opener(NoRedirect()).open(request,timeout=60) as response:
        jobs=json.loads(response.read())
    if not isinstance(jobs,list):raise ValueError('Unexpected job history')
    return jobs


def main():
    approval=json.loads((DEST/'approval-and-quote.json').read_text())
    jobs=fetch_jobs(load_key(),approval['at'])
    rows=[]
    for i,wanted in enumerate(plan()):
        matches=[j for j in jobs if all(j.get(f)==wanted[f] for f in ('dataset','symbols','stype_in','schema'))
                 and ns(j['start'])==ns(wanted['start']) and ns(j['end'])==ns(wanted['end'])]
        if len(matches)>1:raise ValueError('Multiple matching paid jobs; manual reconciliation required')
        known=DEST/('request-%02d'%i)/'submitted.json'
        if known.exists() and (not matches or matches[0]['id']!=json.loads(known.read_text())['id']):
            raise ValueError('Local and provider job records disagree')
        selected=matches[0] if matches else None
        rows.append(dict(request_index=i,request=wanted,provider_job=None if selected is None else
            {k:selected.get(k) for k in ('id','state','cost_usd','record_count','ts_received')},
            status='NO_MATCHING_PROVIDER_JOB_AT_CHECK' if not selected else 'PROVIDER_JOB_IDENTIFIED'))
    accepted=[r for r in rows if r['provider_job']]
    if any(r['provider_job']['state']!='done' for r in accepted):
        cost=None
    else:
        values=[Decimal(str(r['provider_job']['cost_usd'])) for r in accepted]
        if any(not v.is_finite() or v<0 for v in values):raise ValueError('Invalid recorded cost')
        cost=str(sum(values))
    at=datetime.now(timezone.utc)
    result=dict(at=at.isoformat(),status='READ_ONLY_RECONCILIATION',
        accepted_jobs=len(accepted),missing_requests=len(rows)-len(accepted),
        accepted_provider_cost_usd=cost,requests=rows,
        billing_limit_observation='Portal showed $25 monthly limit; no limit changes performed.',
        no_new_jobs_submitted=True,
        note='A missing job here does not authorize retrying an uncertain submission. Preserve intents and reconcile each attempt.')
    target=DEST/('reconciliation-'+at.strftime('%Y%m%dT%H%M%SZ')+'.json')
    save(target,result)
    print(json.dumps({k:v for k,v in result.items() if k!='requests'},indent=2))


if __name__=='__main__':
    try:main()
    except HTTPError as error:
        print('Read-only reconciliation stopped: HTTP',error.code,'(details suppressed)');raise SystemExit(1)
    except Exception as error:
        print('Read-only reconciliation stopped:',type(error).__name__,'(details suppressed)');raise SystemExit(1)
