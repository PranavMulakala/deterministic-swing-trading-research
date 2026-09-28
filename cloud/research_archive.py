"""Offline read-only, point-in-time access to the collector's raw archive."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from research.lite_execution_data.quotes import nanos

NS=1000000000

class DataGap(ValueError): pass

class Archive:
    def __init__(self, folder, asof):
        self.folder=Path(folder)
        self.asof=asof
        self.db=sqlite3.connect((self.folder/'archive.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
        self.db.execute('BEGIN')
        self.used=set()

    def close(self): self.db.close()

    def pages(self, stream, start, end):
        """End-exclusive requested span; complete five-minute source windows only."""
        first=int(start//NS)//300*300
        last=int((end-1)//NS)//300*300
        received=datetime.fromtimestamp(self.asof,timezone.utc).isoformat().replace('+00:00','Z')
        for window in range(first,last+1,300):
            cp=self.db.execute('SELECT end FROM checkpoints WHERE stream=?',(stream,)).fetchone()
            if cp is None or cp[0]<window+300: raise DataGap('stream_not_committed:'+stream)
            rows=list(self.db.execute('SELECT page,received_at,sha256,payload,end FROM pages WHERE stream=? AND start=? ORDER BY page',(stream,window)))
            if not rows or [r[0] for r in rows]!=list(range(len(rows))): raise DataGap('missing_pages:'+stream)
            for i,receipt,digest,payload,stop in rows:
                if stop!=window+300 or nanos(receipt)>int(self.asof*NS): raise DataGap('page_not_available_at_run_cutoff')
                raw=gzip.decompress(payload)
                if hashlib.sha256(raw).hexdigest()!=digest: raise DataGap('source_hash_mismatch')
                value=json.loads(raw)
                if (i==len(rows)-1)!=(value.get('next_page_token') is None): raise DataGap('incomplete_pagination')
                self.used.add((stream,window,i,digest))
                yield value,receipt

    def bars(self, symbol, start, end, five=True):
        by_time={}
        for value,_ in self.pages('bars5' if five else 'bars',start,end):
            group=value.get('bars') or {}
            if not isinstance(group,dict): raise DataGap('invalid_bar_response')
            for row in group.get(symbol,[]):
                t=nanos(row['t'])
                if not start<=t<end: continue
                if t in by_time and by_time[t]!=row: raise DataGap('conflicting_bar_revisions')
                by_time[t]=row
        return [by_time[t] for t in sorted(by_time)]

    def ticks(self, symbol, kind, start, end, cap):
        by_identity={}
        for value,_ in self.pages(symbol+':'+kind,start,end):
            if value.get('symbol')!=symbol: raise DataGap('wrong_tick_symbol')
            for row in value.get(kind) or []:
                t=nanos(row['t'])
                if not start<=t<end: continue
                canonical=json.dumps(row,sort_keys=True,separators=(',',':'))
                # Exact duplicates at inclusive boundaries are retained once.
                # Different quotes at the same timestamp remain conflicts for the frozen engine.
                identity=(t,row.get('x'),row['i']) if kind=='trades' and 'i' in row else canonical
                if identity in by_identity and by_identity[identity]!=row: raise DataGap('conflicting_trade_id')
                by_identity[identity]=row
                if len(by_identity)>cap: raise DataGap('execution_tick_memory_budget')
        return sorted(by_identity.values(),key=lambda r:nanos(r['t']))

    def news(self, start, end, stream='news'):
        if stream not in ('news', 'sector_news'):
            raise DataGap('invalid_news_stream')
        events={}
        for value,receipt in self.pages(stream,start,end):
            for row in value.get('news') or []:
                created=nanos(row['created_at'])
                updated=nanos(row.get('updated_at') or row['created_at'])
                if not start<=created<end:
                    continue
                if updated<created or updated>nanos(receipt):
                    raise DataGap('invalid_news_time')
                identity=(row['id'],row.get('updated_at'))
                old=events.get(identity)
                if old is None or nanos(receipt)<nanos(old['first_received_at']):
                    events[identity]={'article_id':row['id'],'updated_at':row.get('updated_at'),
                                      'created_at':row.get('created_at'),'symbols':row.get('symbols',[]),
                                      'first_received_at':receipt,'source_stream':stream}
        return list(events.values())

    def source_digest(self):
        return hashlib.sha256(json.dumps(sorted(self.used),separators=(',',':')).encode()).hexdigest()
