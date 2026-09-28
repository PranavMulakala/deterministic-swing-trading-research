"""Synthetic quotes only. Never exported as observed market evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from .engine import digest, stamp


def sourced(raw, at, age=0, source='synthetic-fixture'):
    t=(stamp(at)-timedelta(seconds=age)).isoformat()
    result=deepcopy(raw)
    result['provenance']={'source':source,'feed':'fixture-only','published_at':t,
                          'received_at':t,'raw':deepcopy(raw),'sha256':digest(raw)}
    return result


def resign(item):
    raw={k:v for k,v in item.items() if k!='provenance'}
    item['provenance']['raw']=deepcopy(raw)
    item['provenance']['sha256']=digest(raw)
    return item


def packet(at='2026-09-14T14:00:00+00:00', *, ask=65, bid=62, symbol='SPY', event_id=None):
    t=stamp(at)
    day=t.date().isoformat()
    expiry=(t.date()+timedelta(days=10)).isoformat()
    occ=f"{symbol}{datetime.fromisoformat(expiry):%y%m%d}C00502000"
    contract=sourced({'symbol':occ,'underlying':symbol,'right':'C','strike_mills':502000,
                      'expiry':expiry,'expiry_at':expiry+'T20:00:00+00:00','multiplier':100,'adjusted':False,'currency':'USD',
                      'style':'american','open_interest':1000},at)
    q=sourced({'symbol':occ,'market_at':at,'bid_cents':bid,'ask_cents':ask,
               'bid_size':10,'ask_size':10,'volume':200,'condition':'regular'},at)
    end=t.replace(minute=(t.minute//5)*5,second=0,microsecond=0)
    bars=[]
    for i,c in enumerate((500000,501000,502000)):
        btime=(end-timedelta(minutes=(2-i)*5)).isoformat()
        bars.append(sourced({'symbol':symbol,'end':btime,'close_mills':c},btime))
    return {'event_id':event_id or 'fixture-'+at,'kind':'fixture','observed_at':at,'symbol':symbol,
            'calendar':sourced({'date':day,'open':day+'T13:30:00+00:00','close':day+'T20:00:00+00:00'},at),
            'events':sourced({'symbol':symbol,'earnings':'not_applicable_etf','corporate_actions':'clear',
                              'coverage_end':day+'T20:00:00+00:00'},at),
            'news':sourced({'symbol':symbol,'complete':True,'items':[]},at),
            'underlying':sourced({'symbol':symbol,'market_at':at,'price_mills':502000},at),
            'bars':bars,'chain':sourced({'symbol':symbol,'complete':True,'contracts':[{'contract':contract,'quote':q}]},at)}


def scenario():
    return [packet(), packet('2026-09-14T14:00:02+00:00'),
            packet('2026-09-14T16:00:03+00:00',ask=85,bid=82),
            packet('2026-09-14T16:00:05+00:00',ask=85,bid=82)]
