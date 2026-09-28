"""Receipt-time native-bracket comparison model, not a prediction of broker fills.

Resting limits use trade-through as a conservative modeling convention, not an
exchange queue model. Native broker trigger, acknowledgement and cancellation
semantics still require actual paper validation. Nothing here sends orders.
"""
from datetime import datetime,time
import hashlib
import json
from zoneinfo import ZoneInfo

from cloud.ibkr_paper_v1.execution import VERSION,integer,bracket_orders,canonical

NS=1_000_000_000
MODEL='ibkr_native_bracket_receipt_model_v1_candidate'


def simulate(value,events,round_trip_fee_cents=None,entry_latency_ns=100_000_000,
             exit_latency_ns=100_000_000,exit_slippage_ticks=2):
    bracket_orders(value,1)  # Validate the same bracket shape, without transmitting.
    integer(entry_latency_ns);integer(exit_latency_ns);integer(exit_slippage_ticks)
    if round_trip_fee_cents is not None:integer(round_trip_fee_cents)
    direction=value['direction']
    ready=value['planned_at_ns']+entry_latency_ns
    expiry=value['expires_ns']
    noon=int(datetime.combine(datetime.fromisoformat(value['day']).date(),time(12),
                              ZoneInfo('America/New_York')).timestamp())*NS
    last_key=None
    last_quote=None
    first_quote=None
    entry=exit_fill=None
    pending=None
    issues=set()
    digest=hashlib.sha256()
    count=0
    for event in events:
        encoded=canonical(event).encode()
        digest.update(encoded+b'\n');count+=1
        at=integer(event['received_ns'],1)
        key=(at,integer(event['event_id'],1))
        if last_key is not None and key<=last_key:
            raise ValueError('unordered_or_duplicate_tape')
        last_key=key
        if event.get('contract')!=value['contract'] or type(event.get('data_type')) is not int or event['data_type']!=1:
            raise ValueError('unverified_market_event')
        kind=event['kind']
        if kind=='quote':
            bid,ask=integer(event['bid_ticks'],1),integer(event['ask_ticks'],1)
            integer(event['bid_size'],1);integer(event['ask_size'],1)
            if bid>ask:raise ValueError('crossed_book')
        elif kind=='trade':
            price=integer(event['price_ticks'],1)
            integer(event['size'],1)
            if event.get('eligible') is not True:
                raise ValueError('trade_eligibility_not_verified')
        else:raise ValueError('unsupported_market_event')
        if at<value['planned_at_ns']:continue
        if exit_fill is not None:continue
        if kind=='quote':
            if first_quote is None:
                first_quote=at
                if first_quote-value['planned_at_ns']>NS:
                    issues.add('MISSING_INITIAL_QUOTES')
            if last_quote is not None and at-last_quote>NS:
                issues.add('QUOTE_GAP')
            last_quote=at
        elif last_quote is None or at-last_quote>NS:
            issues.add('STALE_QUOTE_AT_TRADE')
        if issues:continue
        if entry is None:
            if kind=='quote' and ready<=at<expiry:
                price=ask if direction==1 else bid
                if direction*(price-value['entry_ticks'])<=0:
                    entry={'at_ns':at,'price_ticks':price,'quantity':1}
            continue
        # A time-exit is only a model convention until cancellation/fill races
        # have been resolved by the actual adapter. Do not imply exact parity.
        if pending is None and at>=noon:
            pending=(noon+exit_latency_ns,'TIME_EXIT_MODEL')
        if pending is not None:
            if kind=='quote' and at>=pending[0]:
                price=(bid-exit_slippage_ticks if direction==1 else ask+exit_slippage_ticks)
                integer(price,1)
                exit_fill={'at_ns':at,'price_ticks':price,'quantity':1,'reason':pending[1]}
            continue
        if kind=='trade':
            if direction*(price-value['stop_ticks'])<=0:
                pending=(at+exit_latency_ns,'LAST_TRIGGERED_STOP_MODEL')
            elif direction*(price-value['target_ticks'])>=1:
                exit_fill={'at_ns':at,'price_ticks':value['target_ticks'],'quantity':1,
                           'reason':'LIMIT_TRADE_THROUGH_MODEL'}
    if issues:
        status='DATA_QUALITY_BLOCKED'
    elif entry is not None and exit_fill is None:
        status='OPEN_POSITION_UNRESOLVED'
    elif entry is None:
        if last_quote is None or last_quote<expiry:
            status='INSUFFICIENT_ENTRY_WINDOW_DATA'
        else:status='NO_MODELED_FILL'
    else:status='MODELED_ROUND_TRIP'
    gross=net=None
    if status=='MODELED_ROUND_TRIP':
        gross=direction*(exit_fill['price_ticks']-entry['price_ticks'])*50
        if round_trip_fee_cents is not None:net=gross-round_trip_fee_cents
    return {'model':MODEL,'execution_version':VERSION,'signal_id':value['signal_id'],
            'status':status,'issues':sorted(issues),'entry':entry,'exit':exit_fill,
            'gross_pnl_cents':gross,'round_trip_fee_cents':round_trip_fee_cents,
            'net_pnl_cents':net,'source_event_count':count,'source_sha256':digest.hexdigest(),
            'time_basis':'LOCAL_RECEIPT_NS','broker_execution_verified':False,
            'fill_probability_established':False,'live_readiness':'NOT_READY',
            'assumptions':{'entry_latency_ns':entry_latency_ns,'exit_latency_ns':exit_latency_ns,
                           'exit_slippage_ticks':exit_slippage_ticks,
                           'target_fill':'TRADE_THROUGH_BY_AT_LEAST_ONE_TICK_NO_QUEUE_MODEL'}}
