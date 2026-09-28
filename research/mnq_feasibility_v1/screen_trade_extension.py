"""Offline audit and signal-only replay of the fixed August trades extension."""
from collections import Counter
from datetime import datetime, timezone
from math import ceil, floor
import json
from pathlib import Path
import struct

from acquire_trade_extension import DEST, plan
from acquire_databento import ROOT, save, sha256
from validate_download import dbn, np, zstandard, ns
from import_databento import TRADE, TradeEvents, independent_bar_check
from engine import bars, signals, timestamp, validate_config

OUT = ROOT/'research/mnq_feasibility_v1/data/trade-extension-import-v1'
REPORT = ROOT/'research/mnq_feasibility_v1/runs/trade-extension-01'
SOURCE = np.dtype(dict(names=['length','rtype','publisher_id','instrument_id','ts_event',
    'price','size','action','side','flags','depth','ts_recv','ts_in_delta','sequence'],
    formats=['u1','u1','<u2','<u4','<u8','<i8','<u4','S1','S1','u1','u1','<u8','<i4','<u4'],
    offsets=[0,1,2,4,8,16,24,28,29,30,31,32,40,44], itemsize=48))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def normalize(arr, row_start, start, end):
    require(len(arr)>0, 'Empty block')
    for name, expected in [('length',12),('rtype',0),('publisher_id',1),
                           ('instrument_id',42004800),('action',b'T')]:
        require(np.all(arr[name]==expected), 'Unexpected '+name)
    require(not np.any(arr['flags'] & (dbn.F_SNAPSHOT|dbn.F_BAD_TS_RECV|dbn.F_MAYBE_BAD_BOOK)), 'Flagged data')
    require(np.all((arr['ts_recv']>=start)&(arr['ts_recv']<end)), 'Capture time outside request')
    require(np.all(arr['ts_event'][1:]>=arr['ts_event'][:-1]), 'Unordered event timestamps')
    require(np.all((arr['price']>0)&(arr['price']!=dbn.UNDEF_PRICE)&
                   (arr['price']%250_000_000==0)&(arr['size']>0)), 'Invalid trade price/size')
    require(np.all(arr['price']//250_000_000 <= np.iinfo(TRADE['price_ticks']).max), 'Trade tick price overflow')
    keep=(arr['ts_event']>=start)&(arr['ts_event']<end)
    selected=arr[keep]
    result=np.zeros(len(selected),TRADE)
    result['ts_ns']=selected['ts_event']
    result['seq']=(np.arange(row_start,row_start+len(arr),dtype='<u8')[keep])*2
    result['price_ticks']=selected['price']//250_000_000
    for name in ('size','ts_recv','flags'):
        result[name]=selected[name]
    result['source_sequence']=selected['sequence']
    return result, int(np.count_nonzero(~keep))


def official_check(block):
    decoder=dbn.DBNDecoder(has_metadata=False,input_version=3)
    rows=decoder.write_and_decode(block)
    arr=np.frombuffer(block,dtype=SOURCE)
    require(len(rows)==len(arr) and not decoder.buffer(), 'Decoder count mismatch')
    for row, source in zip(rows,arr):
        require(isinstance(row,dbn.TradeMsg) and row.record_size()==48, 'Wrong official record')
        for name in ('publisher_id','instrument_id','ts_event','ts_recv','price','size',
                     'flags','depth','sequence','ts_in_delta'):
            require(int(getattr(row,name))==int(source[name]), 'Layout mismatch '+name)
        require(str(row.action).encode()==source['action'], 'Action mismatch')
        require(str(row.side).encode()==source['side'], 'Side mismatch')


def validate_folder(index, request):
    folder=DEST/('request-%02d'%index)
    details=json.loads((folder/'completed-job.json').read_text())
    require(details.get('state')=='done','Job incomplete')
    for field in ('dataset','symbols','stype_in','schema'):
        require(details[field]==request[field],'Job scope mismatch')
    for field in ('start','end'):
        require(ns(details[field])==ns(request[field]),'Job time mismatch')
    meta=json.loads((folder/'files/metadata.json').read_text())
    require(meta['job_id']==details['id'],'Manifest job mismatch')
    require(meta['query']['symbols']==['MNQU6'],'Manifest symbol mismatch')
    require(meta['query']['start']==ns(request['start']) and meta['query']['end']==ns(request['end']), 'Manifest interval mismatch')
    conditions=json.loads((folder/'files/condition.json').read_text())
    require(bool(conditions) and all(c['condition']=='available' for c in conditions), 'Source condition not available')
    listing=json.loads((folder/'file-list.json').read_text())
    require(not list((folder/'files').glob('*.partial')),'Partial files remain')
    for item in listing:
        file=folder/'files'/item['filename']
        require(file.stat().st_size==item['size'] and sha256(file)==item['hash'].removeprefix('sha256:'), 'File integrity mismatch')
    return folder,details,listing


def import_day(index,request):
    folder,details,listing=validate_folder(index,request)
    files=sorted((folder/'files').glob('*.dbn.zst'))
    require(len(files)==1,'Unexpected market file count')
    path=files[0]
    day=request['start'][:10]
    output=OUT/(day+'.trades.bin')
    count=dropped=samples=0
    last_event=last_recv=None
    recv_regressions=0
    flag_counts=Counter()
    start,end=ns(request['start']),ns(request['end'])
    with path.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream, output.open('xb') as target:
        prefix=stream.read(8)
        require(len(prefix)==8 and prefix[:4]==b'DBN\x03','Unsupported DBN version')
        length=struct.unpack('<I',prefix[4:])[0]
        require(length<1_000_000,'Metadata too long')
        meta=dbn.Metadata.decode(prefix+stream.read(length))
        require(meta.dataset=='GLBX.MDP3' and str(meta.schema)=='trades' and
                meta.symbols==['MNQU6'] and not meta.partial and not meta.not_found and
                not meta.ts_out and meta.start==start and meta.end==end,'DBN metadata scope mismatch')
        remainder=b''
        while incoming:=stream.read(48*100_000):
            block=remainder+incoming; whole=len(block)//48*48
            remainder=block[whole:]; block=block[:whole]
            if not block:continue
            arr=np.frombuffer(block,dtype=SOURCE)
            sample=block[:48*min(5,len(arr))]+block[-48*min(5,len(arr)):]
            official_check(sample); samples+=len(sample)//48
            if last_event is not None:
                require(int(arr['ts_event'][0])>=last_event,'Event order across chunks')
                recv_regressions+=int(arr['ts_recv'][0]<last_recv)
            last_event,last_recv=int(arr['ts_event'][-1]),int(arr['ts_recv'][-1])
            recv_regressions+=int(np.count_nonzero(arr['ts_recv'][1:]<arr['ts_recv'][:-1]))
            flags,numbers=np.unique(arr['flags'],return_counts=True)
            flag_counts.update({str(int(f)):int(n) for f,n in zip(flags,numbers)})
            trades,excluded=normalize(arr,count,start,end)
            trades.tofile(target)
            count+=len(arr);dropped+=excluded
        require(not remainder,'Truncated DBN record')
    require(count==details['record_count'],'Provider record count mismatch')
    require(output.stat().st_size>0,'Empty session')
    trades=np.memmap(output,dtype=TRADE,mode='r')
    session=dict(date=day,contract='MNQU6',events=TradeEvents(trades))
    reference=bars(session)
    require(len(reference)==390,'Missing full-session trade minute')
    audit=independent_bar_check(trades,day,reference)
    save(OUT/(day+'.bars.json'),reference)
    row=dict(date=day,contract='MNQU6',source_sha256=sha256(path),
        source_file=str(path.relative_to(ROOT)),trade_file=output.name,
        trade_sha256=sha256(output),raw_record_count=count,trade_count=len(trades),
        excluded_event_boundary_records=dropped,receive_timestamp_regressions=recv_regressions,
        official_decoder_sampled_records=samples,flags=dict(flag_counts),bar_audit=audit)
    print('Audited',day,len(trades),'trades; 390 minutes; excluded boundary',dropped,flush=True)
    return session,reference,row


def independent_signals(day,current,previous,cfg):
    high=max(b['high'] for b in previous.values())
    low=min(b['low'] for b in previous.values())
    result=[]; beyond_up=beyond_down=0
    for i in range(14,119):
        a,b=current[i-1],current[i]
        up=a['sd']>0 and a['close']>a['vwap']+3*a['sd']
        down=a['sd']>0 and a['close']<a['vwap']-3*a['sd']
        beyond_up+=int(up);beyond_down+=int(down)
        side=(-1 if up and a['low']<=high<=a['high'] and b['close']<a['low'] else
              1 if down and a['low']<=low<=a['high'] and b['close']>a['high'] else 0)
        if side:
            result.append(dict(id=f'{day}:{i}:{side}',day=day,contract='MNQU6',
                signal_ns=b['end_ns'],direction=side,
                stop_ticks=min(a['low'],b['low'])-cfg['stop_buffer_ticks'] if side==1 else max(a['high'],b['high'])+cfg['stop_buffer_ticks'],
                target_ticks=floor(b['vwap']) if side==1 else ceil(b['vwap']),
                vwap_ticks=b['vwap'],prior_high_ticks=high,prior_low_ticks=low))
    return result,dict(above_three_sd_minutes=beyond_up,below_three_sd_minutes=beyond_down)


def main():
    root=ROOT/'research/mnq_feasibility_v1'
    pins=json.loads((root/'runs/pre-import-frozen-files.json').read_text())
    require(all(sha256(root/n)==h for n,h in pins.items()),'Frozen file changed')
    summary=json.loads((DEST/'download-summary.json').read_text())
    require(len(summary['requests'])==21,'Acquisition incomplete')
    cfg=json.loads((root/'config.json').read_text());validate_config(cfg)
    OUT.mkdir(exist_ok=False);REPORT.mkdir(exist_ok=False)
    # Validate exact dated definitions before opening market outcomes.
    folder,details,_=validate_folder(20,plan()[20]); definitions=[]
    for file in sorted((folder/'files').glob('*.dbn.zst')):
        decoder=dbn.DBNDecoder(compression=dbn.Compression.ZSTD)
        rows=decoder.write_and_decode(file.read_bytes())
        require(rows and isinstance(rows[0],dbn.Metadata) and not decoder.buffer(),'Definition decode incomplete')
        require(rows[0].symbols==['MNQU6'] and str(rows[0].schema)=='definition','Definition metadata mismatch')
        for r in rows[1:]:
            require(isinstance(r,dbn.InstrumentDefMsg) and r.raw_symbol=='MNQU6' and
                    r.instrument_id==42004800 and r.publisher_id==1 and r.currency=='USD' and
                    r.asset=='MNQ' and str(r.instrument_class)=='F' and
                    r.min_price_increment==250_000_000 and r.unit_of_measure_qty==2_000_000_000 and
                    r.expiration==ns('2026-09-18T13:30:00Z'),'Contract definition mismatch')
            definitions.append(dict(file=file.name,instrument_id=r.instrument_id,raw_symbol=r.raw_symbol))
    require(len(definitions)==details['record_count'] and len(definitions)>0,'Definition count mismatch')
    sessions=[]; found=[]; checks=[]; previous=previous_bars=None
    for index,request in enumerate(plan()[:20]):
        session,current,row=import_day(index,request)
        actual,reason=signals(session,previous,cfg)
        if previous is not None:
            separate,counts=independent_signals(session['date'],current,previous_bars,cfg)
            require(actual==separate,'Independent signal check mismatch')
            require(reason is None,'Signal coverage incomplete')
            checks.append(dict(date=session['date'],patterns=len(actual),**counts))
        else:
            require(not actual and reason=='NO_PREVIOUS_SESSION','Warmup mismatch')
        found.extend(actual);sessions.append(dict(row,patterns=len(actual),warmup=previous is None))
        previous,previous_bars=session,current
    require(all(sha256(root/n)==h for n,h in pins.items()),'Frozen file changed during run')
    result=dict(status='SIGNAL_SCREEN_COMPLETE_NOT_TRADING_READINESS',evidence='HISTORICAL',
        evaluated_sessions=19,warmup_sessions=1,complete_patterns=len(found),
        sessions_with_patterns=len({s['day'] for s in found}),signals=found,sessions=sessions,
        pattern_session_percentage=100*len({s['day'] for s in found})/19,
        risk_fit_percentage=None,net_profit=None,drawdown=None,win_rate=None,
        provider_cost_usd=summary['provider_cost_usd'],
        remaining_extension_budget_usd=summary['remaining_extension_budget_usd'],
        definition_records=len(definitions),independent_signal_checks=checks,
        frozen_files=pins,importer_sha256=sha256(Path(__file__)),
        protocol_sha256=sha256(root/'STAGED_EXTENSION_PROTOCOL.md'),
        limitations=['Trade-only screen has no executable quotes or fills.',
            'This is a feasibility sample, not final untouched validation.',
            '390 trade minutes is coverage evidence, not independent exchange completeness.',
            'Capture-time boundaries may omit late-arriving event-time records.',
            'Fees/margin and actual broker-paper behavior remain unverified.'])
    save(REPORT/'report.json',result)
    save(OUT/'manifest.json',dict(format='MNQ_TRADE_ARRAY_V1',evidence='HISTORICAL',
        sessions=sessions,trade_dtype=TRADE.descr,definitions=definitions))
    message=f'''# August MNQ signal screen

Status: **{result['status']}**.

Audited 20 sessions (one warmup, 19 evaluated) under unchanged rules.
Found **{len(found)} complete patterns on {result['sessions_with_patterns']} days**.
Provider-reported additional data usage: **${float(summary['provider_cost_usd']):.4f}**.
Credit/card settlement has not been checked.

Risk-fit percentage, win rate, net profit, and drawdown are **unknown** because
trade-only records do not supply executable bid/ask prices. No paper or live
orders were placed by this screen.

All session bars were checked with a separate OHLC/VWAP/variance calculation.
Signal enumeration matched a separate pass and frozen file hashes are unchanged.
Detailed source counts, boundary exclusions and caveats are in report.json.

Next: {'quote EVERY signal day within the remaining approved extension budget' if found else 'stop additional acquisition for this version; insufficient signal evidence warrants reviewing the research design'}.
'''
    with (REPORT/'REPORT.md').open('x') as stream:stream.write(message)
    print('SCREEN COMPLETE:',len(found),'patterns across',result['sessions_with_patterns'],'of 19 evaluation sessions.',flush=True)


if __name__=='__main__':main()
