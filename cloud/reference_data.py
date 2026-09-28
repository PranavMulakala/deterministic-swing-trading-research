"""Scheduled GET-only calendar/actions refresh; never account or order access."""
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler
from collector import NoRedirect, iso, SYMBOLS

ALLOWED = {'calendar': ('https://paper-api.alpaca.markets', '/v2/calendar'),
           'actions': ('https://data.alpaca.markets', '/v1/corporate-actions')}

def fetch(kind, query, credentials):
    host, path = ALLOWED[kind]
    opener = build_opener(ProxyHandler({}), NoRedirect())
    req = Request(host + path + '?' + urlencode(query), headers={
        'APCA-API-KEY-ID': credentials['key'], 'APCA-API-SECRET-KEY': credentials['secret']}, method='GET')
    with opener.open(req, timeout=30) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw) > 8*1024*1024: raise ValueError('Oversized metadata')
    return json.loads(raw)

def main():
    folder = Path('/var/lib/trading-collector/references')
    folder.mkdir(exist_ok=True)
    credentials = json.loads(Path('/etc/trading-collector/credentials.json').read_text())
    try:
        calendar = fetch('calendar', {'start':'2026-07-01','end':'2026-12-31'}, credentials)
        if not isinstance(calendar,list) or not calendar: raise ValueError('Invalid calendar')
        pages, seen, token = [], set(), None
        query = {'symbols':','.join(SYMBOLS), 'start':'2026-07-01', 'end':'2026-12-31', 'limit':1000,'sort':'asc'}
        for _ in range(20):
            reply = fetch('actions', {**query, **({'page_token':token} if token else {})}, credentials)
            if not isinstance(reply,dict) or not isinstance(reply.get('corporate_actions'),dict): raise ValueError('Invalid actions')
            pages.append(reply)
            token=reply.get('next_page_token')
            if token is None: break
            if not isinstance(token,str) or not token or token in seen: raise ValueError('Stalled pagination')
            seen.add(token)
        else: raise ValueError('Incomplete action pagination')
        value = {'fetched_at':iso(time.time()), 'calendar':calendar, 'actions':pages, 'query':query,
                 'calendar_endpoint':ALLOWED['calendar'], 'actions_endpoint':ALLOWED['actions'],
                 'label':'provider_snapshot_not_independent_corporate_action_audit'}
        raw = (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
        digest = hashlib.sha256(raw).hexdigest()
        output = folder/(digest+'.json')
        if not output.exists():
            with output.open('xb') as f: f.write(raw)
        temp = folder/'latest.tmp'
        temp.write_text(json.dumps({'file':output.name,'sha256':digest})+'\n')
        temp.replace(folder/'latest.json')
        print(json.dumps({'status':'ok','calendar_sessions':len(calendar),'action_pages':len(pages),'sha256':digest}))
    except Exception as exc:
        print(json.dumps({'status':'error','type':type(exc).__name__}))
        return 1
    return 0

if __name__ == '__main__': raise SystemExit(main())
