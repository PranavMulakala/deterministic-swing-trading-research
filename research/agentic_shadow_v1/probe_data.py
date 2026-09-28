"""One GET-only entitlement probe using the existing personal credential loader.

Not used by the isolated simulation service. No account/order/permission endpoints.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from swingbot.paper_cli import _load_env, ALLOWED_ENV_KEYS

URL='https://data.alpaca.markets/v1beta1/options/snapshots/SPY?feed=opra&limit=1'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('redirect_refused')


def probe():
    root=Path(__file__).resolve().parents[2]
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'source':URL,'method':'GET','feed':'opra',
            'orders':False,'subscriptions_changed':False}
    before={name:os.environ.get(name) for name in ALLOWED_ENV_KEYS}
    try:
        if not all(os.environ.get(k) for k in ('ALPACA_PAPER_API_KEY','ALPACA_PAPER_API_SECRET')):
            _load_env(root/'.env')
        key=os.environ.get('ALPACA_PAPER_API_KEY','')
        secret=os.environ.get('ALPACA_PAPER_API_SECRET','')
    except (ValueError,PermissionError,OSError):
        return {**result,'status':'BLOCKED','reason':'existing_credential_loader_rejected_local_env; no network request made'}
    finally:
        # The existing loader mutates process environment line by line. Restore
        # every allowed key on success or failure so retries cannot use a partial load.
        for name,value in before.items():
            if value is None: os.environ.pop(name,None)
            else: os.environ[name]=value
    if not key or not secret:
        return {**result,'status':'BLOCKED','reason':'existing_personal_paper_credentials_missing'}
    request=Request(URL,headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret},method='GET')
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=15) as response:
            raw=response.read(1024*1024+1)
        if len(raw)>1024*1024:
            raise ValueError('response_too_large')
        payload=json.loads(raw)
        records=payload.get('snapshots',{})
        return {**result,'status':'SAMPLE_ONLY' if records else 'BLOCKED','reason':'not_complete_session_coverage',
                'records':len(records),'payload_sha256':hashlib.sha256(raw).hexdigest()}
    except HTTPError as exc:
        return {**result,'status':'BLOCKED','reason':'opra_http_'+str(exc.code)}
    except (URLError,OSError,ValueError,TypeError,AttributeError):
        return {**result,'status':'BLOCKED','reason':'transport_or_payload_failure'}

if __name__=='__main__':
    print(json.dumps(probe(),indent=2))
