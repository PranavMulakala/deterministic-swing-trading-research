"""Interactive, ephemeral-key metadata quote. Cannot submit a data download.

Uses only Python's standard library and Databento's metadata API. No environment
keys, .env, clipboard access, key files, SDK installation, or redirected requests.
"""
import base64
from datetime import datetime, timezone
from decimal import Decimal
import getpass
import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
import sys
import uuid
import warnings
from urllib.parse import urlencode

HOST = 'hist.databento.com'
METHODS = frozenset(('get_cost', 'get_record_count'))
DAYS = ('2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03', '2026-09-04')


def plan():
    return [{'dataset': 'GLBX.MDP3', 'symbols': 'MNQU6', 'stype_in': 'raw_symbol',
             'schema': 'mbp-1', 'start': d+'T13:30:00Z', 'end': d+'T20:00:00Z'} for d in DAYS]


def validate_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'db-[A-Za-z0-9_-]{29}', key):
        raise ValueError('Expected a 32-character Databento key starting with db-.')


def build_request(method, params, key):
    validate_key(key)
    if method not in METHODS or params not in plan():
        raise ValueError('Only the five fixed MNQU6 metadata requests are allowed.')
    path = '/v0/metadata.' + method
    body = urlencode(params).encode('ascii')
    headers = {'Authorization': 'Basic '+base64.b64encode((key+':').encode('ascii')).decode('ascii'),
               'Content-Type': 'application/x-www-form-urlencoded',
               'User-Agent': 'personal-mnq-quote-only/1'}
    return path, body, headers


def metadata(method, params, key):
    path, body, headers = build_request(method, params, key)
    # http.client does not follow redirects or pick up environment proxy settings.
    conn = http.client.HTTPSConnection(HOST, timeout=45, context=ssl.create_default_context())
    try:
        conn.request('POST', path, body=body, headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            # Never echo provider bodies, headers or request objects (could contain secrets).
            raise RuntimeError(f'Metadata request failed: HTTP {response.status}. No download submitted.')
        raw = response.read(4097)
        if len(raw) > 4096:
            raise RuntimeError('Unexpected metadata response size. Stopped.')
        value = json.loads(raw, parse_float=Decimal)
        if method == 'get_record_count':
            if type(value) is not int or value <= 0:
                raise RuntimeError('No positive record count; check symbol, date and access in the portal.')
        else:
            if type(value) not in (int, Decimal) or not Decimal(value).is_finite() or value < 0:
                raise RuntimeError('Invalid numeric cost response. Stopped.')
        return value
    finally:
        conn.close()


def collect_quotes(key, requester=metadata):
    rows = []
    for params in plan():
        print('Checking '+params['start'][:10]+' ...', flush=True)
        records = requester('get_record_count', params, key)
        cost = requester('get_cost', params, key)
        rows.append({'request': params, 'records': records, 'quoted_usd': str(cost)})
        print(f'  {records:,} records; quoted cost ${Decimal(cost):.6f}', flush=True)
    total = sum((Decimal(r['quoted_usd']) for r in rows), Decimal(0))
    return {'status': 'QUOTE_ONLY_NO_DOWNLOAD_SUBMITTED', 'created_at': datetime.now(timezone.utc).isoformat(),
            'rows': rows, 'total_quoted_usd': str(total), 'within_25_dollar_usage_budget': total <= 25,
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limits': ['Quote covers MBP-1 windows only; definitions/calendar/source validation remain separate.',
                       'Account credit balance and remaining monthly allowance were not read by this helper.',
                       'An estimate below $25 does not automatically authorize a download.',
                       'Positive record counts do not verify contract definitions or data completeness.']}


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('Run in an interactive Terminal. Refusing piped or visible secret input.')
        return 1
    print('MNQ QUOTE ONLY — no downloads, subscriptions, or trading.\n'
          'Five regular sessions, MNQU6, MBP-1.\n'
          'Your key is used in this process only; it is not saved.\n'
          'Paste the key at the next prompt and press Return. Nothing will appear as you paste.\n')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            key = getpass.getpass('Databento API key (hidden): ')
        validate_key(key)
        report = collect_quotes(key)
        del key
        folder = Path(__file__).resolve().parent / 'quotes'
        folder.mkdir(exist_ok=True)
        output = folder / ('quote-'+uuid.uuid4().hex+'.json')
        with output.open('x') as f:
            json.dump(report, f, indent=2, allow_nan=False)
            f.write('\n')
        print('\nTotal quote: $'+report['total_quoted_usd'])
        print('No download was submitted. Key was not saved.')
        print('Non-secret result saved to: '+str(output))
        return 0
    except KeyboardInterrupt:
        print('\nCancelled. No download submitted.')
        return 1
    except Exception as exc:
        # Even a unexpected TLS/JSON/provider exception is summarized, not dumped.
        # Numeric HTTP status is safe, but arbitrary exception text is never printed.
        if isinstance(exc, http.client.HTTPException):
            category = 'HTTP transport error'
        elif isinstance(exc, ssl.SSLError):
            category = 'TLS verification error'
        elif isinstance(exc, (TimeoutError, ConnectionError, OSError)):
            category = 'Network or local file error'
        elif isinstance(exc, ValueError):
            category = 'Invalid key format or response'
        else:
            category = 'Metadata request rejected or unexpected response'
        print('\nStopped: '+category+'. No download submitted. Key not saved.')
        print('Tell Codex this status text only, not your API key.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
