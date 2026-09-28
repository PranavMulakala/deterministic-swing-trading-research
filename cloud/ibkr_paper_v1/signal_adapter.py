"""Causal receipt-time MNQ minute calculations; no broker or order routing.

The arithmetic follows the frozen strategy. The time basis is explicitly
different from the historical exchange-time tape, and needs separate validation.
"""
from datetime import datetime,time
from math import ceil,floor,sqrt
from zoneinfo import ZoneInfo

NS=1_000_000_000
MINUTE=60*NS
NY=ZoneInfo('America/New_York')


def session_start(day):
    return int(datetime.combine(datetime.fromisoformat(day).date(),time(9,30),NY).timestamp())*NS


class MinuteStream:
    def __init__(self,day,contract,previous_bars=None,previous_contract=None):
        self.day,self.contract=day,contract
        self.start=session_start(day)
        self.next_close=0
        self.weight=self.mean=self.m2=0.0
        self.bars={}
        self.signals=[]
        self.last_received=None
        self.halt=None
        self.prior_high=self.prior_low=None
        if previous_bars is not None and previous_contract==contract and set(previous_bars)==set(range(390)):
            self.prior_high=max(x['high'] for x in previous_bars.values())
            self.prior_low=min(x['low'] for x in previous_bars.values())
        self.warmup_ready=self.prior_high is not None

    def _close(self,index,observed_ns):
        if index not in self.bars:
            self.halt=self.halt or 'MISSING_TRADE_MINUTE'
            return
        if self.halt or not self.warmup_ready or not 14<=index<119:
            return
        a,b=self.bars[index-1],self.bars[index]
        direction=0
        if (a['sd']>0 and a['close']>a['vwap']+3*a['sd']
                and a['low']<=self.prior_high<=a['high'] and b['close']<a['low']):
            direction=-1
        elif (a['sd']>0 and a['close']<a['vwap']-3*a['sd']
                and a['low']<=self.prior_low<=a['high'] and b['close']>a['high']):
            direction=1
        if not direction:return
        stop=(min(a['low'],b['low'])-2 if direction==1 else max(a['high'],b['high'])+2)
        self.signals.append({'id':f'{self.day}:{index}:{direction}','day':self.day,
            'contract':self.contract,'signal_ns':b['end_ns'],'generated_received_ns':observed_ns,
            'direction':direction,'stop_ticks':stop,
            'target_ticks':floor(b['vwap']) if direction==1 else ceil(b['vwap']),
            'vwap_ticks':b['vwap'],'prior_high_ticks':self.prior_high,'prior_low_ticks':self.prior_low,
            'time_basis':'LOCAL_RECEIPT_NS','strategy_evidence_approved':False})

    def advance(self,received_ns):
        if type(received_ns) is not int:raise ValueError('integer_timestamp_required')
        if self.last_received is not None and received_ns<self.last_received:
            self.halt=self.halt or 'RECEIPT_CLOCK_MOVED_BACKWARD'
            raise ValueError('receipt_time_regressed')
        self.last_received=received_ns
        closed=min(390,max(0,(received_ns-self.start)//MINUTE))
        while self.next_close<closed:
            self._close(self.next_close,received_ns)
            self.next_close+=1

    def trade(self,received_ns,price_ticks,size):
        if (type(price_ticks) is not int or price_ticks<=0
                or type(size) is not int or size<=0):
            self.halt=self.halt or 'INVALID_TRADE'
            raise ValueError('positive_integer_trade_required')
        if not self.start<=received_ns<self.start+390*MINUTE:
            raise ValueError('outside_regular_session')
        self.advance(received_ns)
        index=(received_ns-self.start)//MINUTE
        if index<self.next_close:
            self.halt=self.halt or 'LATE_CLOSED_MINUTE_EVENT'
            raise ValueError('closed_minute_is_immutable')
        total=self.weight+size
        delta=price_ticks-self.mean
        self.mean+=delta*size/total
        self.m2+=size*delta*(price_ticks-self.mean)
        self.weight=total
        bar=self.bars.setdefault(index,{'open':price_ticks,'high':price_ticks,'low':price_ticks})
        bar.update(high=max(bar['high'],price_ticks),low=min(bar['low'],price_ticks),
                   close=price_ticks,vwap=self.mean,sd=sqrt(max(0,self.m2/self.weight)),
                   end_ns=self.start+(index+1)*MINUTE)

    def minute_coverage_complete(self):
        """Only bar coverage, not feed completeness or execution readiness."""
        return self.next_close==390 and self.halt is None and set(self.bars)==set(range(390))
