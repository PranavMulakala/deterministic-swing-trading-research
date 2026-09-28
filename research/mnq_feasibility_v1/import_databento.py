"""Offline, fixed-scope DBN-to-array adapter. See IMPORT_PROTOCOL.md."""
from collections import Counter
import json
from pathlib import Path
import struct
import sys
from math import isclose

from validate_download import DTYPE, dbn, np, zstandard, check_header, ns
from acquire_databento import DEST, ROOT, plan, save, sha256

OUT = ROOT / 'research/mnq_feasibility_v1/data/import-v1'
TRADE = np.dtype([('ts_ns','<u8'),('seq','<u8'),('price_ticks','<u4'),('size','<u4'),
                  ('ts_recv','<u8'),('source_sequence','<u4'),('flags','u1')])
QUOTE = np.dtype([('ts_ns','<u8'),('seq','<u8'),('bid_ticks','<u4'),('ask_ticks','<u4'),
                  ('bid_size','<u4'),('ask_size','<u4'),('ts_recv','<u8'),
                  ('source_sequence','<u4'),('flags','u1')])
TICK = 250_000_000


def normalize(arr, source_row, start, end):
    check_header(arr)
    if np.any(arr['flags'] & (dbn.F_SNAPSHOT | dbn.F_BAD_TS_RECV | dbn.F_MAYBE_BAD_BOOK)):
        raise ValueError('Flagged source records require a separate importer policy')
    if not np.all(np.isin(arr['action'], [b'A', b'C', b'M', b'T', b'R', b'N'])):
        raise ValueError('Unsupported action')
    if np.any(arr['ts_event'][1:] < arr['ts_event'][:-1]):
        raise ValueError('Unordered source')
    included = (arr['ts_event'] >= start) & (arr['ts_event'] < end)
    ordinal = np.arange(source_row, source_row + len(arr), dtype='<u8')
    trades = included & (arr['action'] == b'T')
    quotes = included & ((arr['flags'] & dbn.F_LAST) != 0)
    t, q = np.zeros(np.count_nonzero(trades), TRADE), np.zeros(np.count_nonzero(quotes), QUOTE)
    for mask, output, add in [(trades,t,0),(quotes,q,1)]:
        source = arr[mask]
        output['ts_ns'] = source['ts_event']
        output['seq'] = ordinal[mask] * 2 + add
        output['ts_recv'] = source['ts_recv']
        output['source_sequence'] = source['sequence']
        output['flags'] = source['flags']
    source = arr[trades]
    if np.any((source['price'] <= 0) | (source['price'] == dbn.UNDEF_PRICE) |
              (source['price'] % TICK != 0) | (source['size'] == 0)):
        raise ValueError('Invalid trade')
    t['price_ticks'], t['size'] = source['price'] // TICK, source['size']
    for side in ['bid','ask']:
        values = arr[quotes][side + '_px_00']
        defined = values != dbn.UNDEF_PRICE
        if np.any(defined & ((values < 0) | (values % TICK != 0))):
            raise ValueError('Invalid quote price')
        q[side + '_ticks'] = np.where(defined, values // TICK, 0)
        q[side + '_size'] = arr[quotes][side + '_sz_00']
    return t, q, int(np.count_nonzero(~included))


class TradeEvents:
    def __init__(self, array):
        self.array = array

    def __iter__(self):
        for row in self.array:
            yield dict(type='trade', ts_ns=int(row['ts_ns']), seq=int(row['seq']),
                       price_ticks=int(row['price_ticks']), size=int(row['size']))


def independent_bar_check(trades, day, reference):
    start = ns(day + 'T13:30:00Z')
    minutes = (trades['ts_ns'] - start) // 60_000_000_000
    max_vwap_difference = max_sd_difference = 0.0
    weight = weighted_centered = weighted_centered_squared = np.longdouble(0)
    # Center prices to reduce cancellation in this separate moment calculation.
    origin = int(trades['price_ticks'][0])
    for minute in range(390):
        left, right = np.searchsorted(minutes, [minute, minute+1])
        rows = trades[left:right]
        if not len(rows) or minute not in reference:
            raise ValueError('Missing minute')
        px = rows['price_ticks'].astype(np.longdouble)
        sizes = rows['size'].astype(np.longdouble)
        centered = px - origin
        weight += sizes.sum()
        weighted_centered += (centered * sizes).sum()
        weighted_centered_squared += (centered * centered * sizes).sum()
        vwap = origin + weighted_centered / weight
        variance = weighted_centered_squared / weight - (weighted_centered / weight)**2
        sd = float(np.sqrt(max(np.longdouble(0), variance)))
        b = reference[minute]
        if (b['open'],b['high'],b['low'],b['close']) != tuple(map(int,[px[0],px.max(),px.min(),px[-1]])):
            raise ValueError('Independent OHLC check failed')
        max_vwap_difference = max(max_vwap_difference, abs(float(vwap)-b['vwap']))
        max_sd_difference = max(max_sd_difference, abs(sd-b['sd']))
        if not isclose(float(vwap), b['vwap'], abs_tol=1e-5, rel_tol=0) or not isclose(sd,b['sd'],abs_tol=1e-5,rel_tol=0):
            raise ValueError('Independent VWAP/variance check failed')
    return dict(minutes_verified=390, maximum_vwap_tick_difference=max_vwap_difference,
                maximum_sd_tick_difference=max_sd_difference)


def main():
    from engine import bars
    OUT.mkdir(exist_ok=False)
    sessions = []
    for i, request in enumerate(plan()[:5]):
        day = request['start'][:10]
        folder = DEST / ('request-%02d' % i)
        listing = json.loads((folder/'file-list.json').read_text())
        item = next(x for x in listing if x['filename'].endswith('.dbn.zst'))
        source = folder/'files'/item['filename']
        if sha256(source) != item['hash'].removeprefix('sha256:'):
            raise ValueError('Source changed')
        count = dropped = trade_count = quote_count = 0
        last_event = None
        trade_file, quote_file = OUT/(day+'.trades.bin'), OUT/(day+'.quotes.bin')
        with source.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, trade_file.open('xb') as tf, quote_file.open('xb') as qf:
            prefix = stream.read(8)
            if prefix[:4] != b'DBN\x03': raise ValueError('Unsupported DBN version')
            length = struct.unpack('<I',prefix[4:])[0]
            metadata = dbn.Metadata.decode(prefix+stream.read(length))
            if metadata.symbols != ['MNQU6'] or str(metadata.schema) != 'mbp-1' or metadata.ts_out:
                raise ValueError('Wrong metadata')
            start,end=ns(request['start']),ns(request['end'])
            if metadata.start != start or metadata.end != end: raise ValueError('Wrong request window')
            remainder=b''
            while incoming := stream.read(80*100_000):
                block=remainder+incoming; whole=len(block)//80*80
                remainder=block[whole:]; arr=np.frombuffer(block[:whole],dtype=DTYPE)
                if not len(arr):continue
                if last_event is not None and int(arr['ts_event'][0]) < last_event:raise ValueError('Unordered boundary')
                last_event=int(arr['ts_event'][-1])
                t,q,n=normalize(arr,count,start,end)
                t.tofile(tf);q.tofile(qf)
                count+=len(arr);trade_count+=len(t);quote_count+=len(q);dropped+=n
            if remainder:raise ValueError('Truncated record')
        details=json.loads((folder/'completed-job.json').read_text())
        if count!=details['record_count']:raise ValueError('Wrong source record count')
        trades=np.memmap(trade_file,dtype=TRADE,mode='r')
        reference=bars(dict(date=day,events=TradeEvents(trades)))
        audit=independent_bar_check(trades,day,reference)
        save(OUT/(day+'.bars.json'),reference)
        row=dict(date=day,previous_date=sessions[-1]['date'] if sessions else None,
            contract='MNQU6', regular_session_complete=True, coverage_status='OBSERVED_390_MINUTES_NOT_INDEPENDENT_EXCHANGE_COMPLETENESS',
            source_file=str(source.relative_to(ROOT)),source_sha256=sha256(source),raw_records=count,
            excluded_event_boundary_records=dropped,trade_count=trade_count,quote_count=quote_count,
            trades=trade_file.name,quotes=quote_file.name,trade_sha256=sha256(trade_file),
            quote_sha256=sha256(quote_file),bar_audit=audit)
        sessions.append(row)
        print('Imported',day,trade_count,'trades,',quote_count,'completed-event quotes; bar audit passed',flush=True)
    save(OUT/'manifest.json',dict(format='MNQ_ARRAY_V1',evidence='HISTORICAL',time_basis='exchange_event_time',
        source='Databento approved pilot; original hashes and row identities retained',
        sessions=sessions,trade_dtype=TRADE.descr,quote_dtype=QUOTE.descr,
        adapter_sha256=sha256(Path(__file__)),protocol_sha256=sha256(ROOT/'research/mnq_feasibility_v1/IMPORT_PROTOCOL.md')))
    print('Import complete:',OUT,flush=True)


if __name__=='__main__':main()
