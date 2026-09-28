"""Standalone delayed SIP archive. No broker client, orders, or strategy execution."""
import argparse
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

STOCKS = ('LITE', 'COHR', 'CIEN', 'FN', 'AAOI')
ETFS = ('SPY', 'QQQ', 'IWM', 'DIA', 'XLB', 'XLE', 'XLF', 'XLI', 'XLK',
        'XLP', 'XLRE', 'XLU', 'XLV', 'XLY', 'XLC')
SYMBOLS = ETFS + STOCKS
NEWS_CONTEXT = json.loads(Path(__file__).with_name('news_context_v1.json').read_text())
CONTEXT_SYMBOLS = tuple(NEWS_CONTEXT['symbols'])
if (not CONTEXT_SYMBOLS or len(CONTEXT_SYMBOLS) != len(set(CONTEXT_SYMBOLS))
        or any(not isinstance(s, str) or not s.isalnum() or s != s.upper() for s in CONTEXT_SYMBOLS)):
    raise ValueError('Invalid context-news symbols')
STREAMS = ('bars', 'bars5', 'news', 'sector_news') + tuple(f'{s}:{k}' for s in STOCKS for k in ('quotes', 'trades'))
HOST = 'https://data.alpaca.markets'
STEP = 300
DELAY = 1200
MAX_PAGE = 16 * 1024 * 1024


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace('+00:00', 'Z')


def stamp(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timezone required')
    return int(d.timestamp())


def request_spec(stream, start, end):
    if stream not in STREAMS or end - start != STEP:
        raise ValueError('Outside collection scope')
    q = dict(start=iso(start), end=iso(end), sort='asc')
    if stream in ('news', 'sector_news'):
        symbols = SYMBOLS if stream == 'news' else CONTEXT_SYMBOLS
        return '/v1beta1/news', dict(q, symbols=','.join(symbols), limit=50, include_content='false')
    q.update(feed='sip', asof='-', limit=10000)
    if stream in ('bars', 'bars5'):
        return '/v2/stocks/bars', dict(q, symbols=','.join(SYMBOLS), timeframe='5Min' if stream == 'bars5' else '1Min', adjustment='raw')
    symbol, kind = stream.split(':')
    return f'/v2/stocks/{symbol}/{kind}', q


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect forbidden')


class Client:
    def __init__(self, credentials):
        self.headers = {'APCA-API-KEY-ID': credentials['key'], 'APCA-API-SECRET-KEY': credentials['secret']}
        if not all(isinstance(v, str) and v.strip() for v in self.headers.values()):
            raise ValueError('Missing credentials')
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def get(self, stream, start, end, token):
        path, q = request_spec(stream, start, end)
        if token is not None:
            q['page_token'] = token
        time.sleep(0.45)  # below Basic's 200 requests/minute; one process only
        request = Request(HOST + path + '?' + urlencode(q), headers=self.headers, method='GET')
        with self.opener.open(request, timeout=30) as response:
            raw = response.read(MAX_PAGE + 1)
        if len(raw) > MAX_PAGE:
            raise ValueError('Oversized response')
        return raw


def validate(stream, body):
    if not isinstance(body, dict):
        raise ValueError('Invalid response')
    kind = 'bars' if stream == 'bars5' else 'news' if stream in ('news', 'sector_news') else stream.split(':')[-1]
    rows = body.get(kind)
    if kind not in body:
        raise ValueError('Missing data field')
    if rows is None:
        rows = {} if stream in ('bars', 'bars5') else []
    if stream in ('bars', 'bars5'):
        if not isinstance(rows, dict) or set(rows) - set(SYMBOLS):
            raise ValueError('Invalid bar symbols')
        groups = list(rows.values())
    else:
        if stream not in ('news', 'sector_news') and body.get('symbol') != stream.split(':')[0]:
            raise ValueError('Wrong symbol')
        groups = [rows]
    count = 0
    for group in groups:
        if not isinstance(group, list) or any(not isinstance(r, dict) for r in group):
            raise ValueError('Invalid rows')
        for row in group:
            if stream not in ('news', 'sector_news'):
                stamp(row['t'])
            elif ('id' not in row or not isinstance(row.get('symbols'), list)
                  or not isinstance(row.get('created_at'), str)):
                raise ValueError('Invalid news metadata')
            else:
                stamp(row['created_at'])
                stamp(row.get('updated_at') or row['created_at'])
                if any(not isinstance(s, str) for s in row['symbols']):
                    raise ValueError('Invalid news symbols')
        count += len(group)
    token = body.get('next_page_token')
    if token is not None and (not isinstance(token, str) or not token):
        raise ValueError('Invalid pagination')
    return count, token


def database(path):
    db = sqlite3.connect(path, timeout=30)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS pages (
        stream TEXT, start INTEGER, end INTEGER, page INTEGER, received_at TEXT,
        sha256 TEXT, records INTEGER, payload BLOB,
        PRIMARY KEY(stream,start,page));
      CREATE TABLE IF NOT EXISTS checkpoints (stream TEXT PRIMARY KEY, end INTEGER);
      CREATE TABLE IF NOT EXISTS health (stream TEXT PRIMARY KEY, checked_at TEXT, error TEXT);
    ''')
    return db


def collect_window(db, client, stream, start, end):
    token, seen, total = None, set(), 0
    with db:
        for page in range(300):
            raw = client.get(stream, start, end, token)
            received = iso(time.time())
            count, token = validate(stream, json.loads(raw))
            db.execute('INSERT INTO pages VALUES (?,?,?,?,?,?,?,?)',
                       (stream, start, end, page, received, hashlib.sha256(raw).hexdigest(), count,
                        gzip.compress(raw, mtime=0)))
            total += count
            if token is None:
                db.execute('INSERT OR REPLACE INTO checkpoints VALUES (?,?)', (stream, end))
                return total
            if token in seen:
                raise ValueError('Repeated pagination token')
            seen.add(token)
        raise ValueError('Pagination cap reached; checkpoint not advanced')


def space_ok(folder):
    return shutil.disk_usage(folder).free >= 5 * 1024**3


def cycle(db, client, initial, now, folder):
    target = int((now - DELAY) // STEP) * STEP
    counts = {}
    for stream in STREAMS:
        row = db.execute('SELECT end FROM checkpoints WHERE stream=?', (stream,)).fetchone()
        prospective = stamp(NEWS_CONTEXT['collection_start']) if stream == 'sector_news' else initial
        start = row[0] if row else max(initial, prospective)
        if start + STEP > target:
            continue
        try:
            if not space_ok(folder):
                raise OSError('Disk reserve reached')
            count = collect_window(db, client, stream, start, start + STEP)
            error = None
            counts[stream] = count
        except Exception as exc:
            # Never log provider bodies, exception messages, or credentials.
            error = type(exc).__name__ + (f':{exc.code}' if isinstance(exc, HTTPError) else '')
        with db:
            db.execute('INSERT OR REPLACE INTO health VALUES (?,?,?)', (stream, iso(time.time()), error))
    return counts


def status(db, initial):
    ends = dict(db.execute('SELECT stream,end FROM checkpoints'))
    errors = {s: e for s, _, e in db.execute('SELECT * FROM health') if e}
    return {'at': iso(time.time()), 'mode': 'DELAYED_RESEARCH_ONLY_NO_ORDERS',
            'news_context': {'id': NEWS_CONTEXT['id'], 'start': NEWS_CONTEXT['collection_start'],
                             'symbols': len(CONTEXT_SYMBOLS), 'selection': False},
            'initial_start': iso(initial), 'completed_through': {s: iso(t) for s,t in ends.items()},
            'pending_streams': [s for s in STREAMS if s not in ends], 'errors': errors,
            'pages': db.execute('SELECT count(*) FROM pages').fetchone()[0],
            'records': db.execute('SELECT coalesce(sum(records),0) FROM pages').fetchone()[0]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', default='/var/lib/trading-collector')
    p.add_argument('--credentials', default='/etc/trading-collector/credentials.json')
    p.add_argument('--start', default='2026-09-08T00:00:00Z')
    p.add_argument('--once', action='store_true')
    args = p.parse_args()
    initial = stamp(args.start)
    if initial % STEP:
        p.error('Start must align to a 5-minute boundary')
    folder = Path(args.data)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = database(folder / 'archive.sqlite')
        client = Client(json.loads(Path(args.credentials).read_text()))
        while True:
            counts = cycle(db, client, initial, time.time(), folder)
            summary = status(db, initial)
            tmp = folder / 'health.tmp'
            tmp.write_text(json.dumps(summary, indent=2) + '\n')
            tmp.replace(folder / 'health.json')
            print(json.dumps({'at': summary['at'], 'windows': len(counts),
                              'new_records': sum(counts.values()), 'errors': summary['errors']}), flush=True)
            if args.once:
                return 1 if summary['errors'] else 0
            time.sleep(5 if counts else 60)


if __name__ == '__main__':
    main()
