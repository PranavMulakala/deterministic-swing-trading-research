"""Validate fresh broker observations before changing an execution ledger.

No socket and no ledger mutation. Query-end callbacks are evidence of completed
queries, not an atomic broker snapshot or permission to retry an uncertain order.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from cloud.ibkr_paper_v1.execution import ACCOUNT, SYMBOL, NS, integer

ENDS = {'positions', 'orders', 'executions', 'summary'}
INFO_CODES = {2104, 2106, 2107, 2108, 2158}


def epoch_ns(value):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError('snapshot_timezone_missing')
    delta = stamp.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * NS + delta.microseconds * 1000


def exact_units(value, multiplier=1, nonnegative=True):
    if type(value) not in (str, int):
        raise ValueError('invalid_decimal_type')
    try:
        number = Decimal(value) * multiplier
    except InvalidOperation as exc:
        raise ValueError('invalid_decimal') from exc
    if (not number.is_finite() or abs(number) > 10**12
            or number != number.to_integral_value() or (nonnegative and number < 0)):
        raise ValueError('unsupported_decimal_precision_or_range')
    return int(number)


def load(path, expected_sha256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('snapshot_hash_mismatch')
    return json.loads(raw)


def inspect(snapshot, owned_orders, contract_id, client_id, now_ns, after_ns):
    """Inspect a completed capture newer than the last relevant broker action.

    owned_orders maps order IDs to expected side, order_ref and optional perm_id.
    Only a flat, exclusive research account is eligible for the returned flat
    observation. Unknown positions/orders/executions require manual review.
    Fee amounts not exactly representable in cents are retained as unresolved,
    rather than silently rounded into an allegedly exact ledger.
    """
    integer(now_ns,1); integer(after_ns,1); integer(contract_id,1); integer(client_id,1)
    if (snapshot.get('version') != 1 or snapshot.get('mode') != 'PAPER_READ_ONLY'
            or snapshot.get('paper_account_verified') is not True
            or snapshot.get('failure') is not None
            or snapshot.get('orders_sent') is not False
            or snapshot.get('snapshot_is_atomic') is not False):
        raise ValueError('successful_paper_snapshot_required')
    if (snapshot.get('execution_history_scope') != 'BROKER_API_AVAILABLE_WINDOW_NOT_FULL_ACCOUNT_HISTORY'
            or set(snapshot.get('query_end_markers',{})) != ENDS
            or any(v is not True for v in snapshot['query_end_markers'].values())):
        raise ValueError('query_scope_or_end_markers_missing')
    if any(e.get('code') not in INFO_CODES for e in snapshot.get('errors',[])):
        raise ValueError('broker_error_requires_review')
    started, ended = epoch_ns(snapshot['started_at']), epoch_ns(snapshot['ended_at'])
    if not after_ns <= started <= ended <= now_ns:
        raise ValueError('snapshot_precedes_action_or_has_bad_clock')
    if now_ns-ended > 5*NS or ended-started > 30*NS:
        raise ValueError('stale_or_overlong_snapshot')
    seen_ends = set()
    previous = started
    executions, commissions = {}, {}
    position_ids = set()
    for r in snapshot['records']:
        received = integer(r['receipt_ns'],1)
        if not previous <= received <= ended:
            raise ValueError('snapshot_callback_clock_regressed')
        previous = received
        kind = r['kind']
        if kind.endswith('_end'):
            category = kind[:-4]
            if category not in ENDS or category in seen_ends:
                raise ValueError('unexpected_or_duplicate_end_marker')
            seen_ends.add(category)
            continue
        category = {'position':'positions','order':'orders','execution':'executions','summary':'summary'}.get(kind)
        if category in seen_ends:
            raise ValueError('account_changed_after_query_end')
        if kind == 'position':
            con_id=integer(r['con_id'],1)
            if con_id in position_ids:
                raise ValueError('position_changed_during_snapshot')
            position_ids.add(con_id)
            if exact_units(r['quantity'], nonnegative=False) != 0:
                raise ValueError('broker_position_not_flat')
        elif kind == 'order':
            # Even a different asset can indicate competing manual/API activity.
            raise ValueError('broker_orders_still_open')
        elif kind == 'execution':
            order_id = integer(r['order_id'],1)
            owned = owned_orders.get(order_id)
            side = {'BOT':'BUY','SLD':'SELL'}.get(r['side'])
            if (owned is None or r['client_id'] != client_id
                    or r['contract'] != SYMBOL or r['con_id'] != contract_id
                    or side != owned['side'] or r['order_ref'] != owned['order_ref']
                    or (owned.get('perm_id') is not None and r['perm_id'] != owned['perm_id'])
                    or r.get('pending_price_revision') is not False
                    or exact_units(r['quantity']) != 1):
                raise ValueError('unowned_or_unsettled_execution')
            exec_id = r['execution_id']
            if not isinstance(exec_id,str) or not exec_id:
                raise ValueError('missing_execution_identity')
            normalized = {'execution_id':exec_id,'order_id':order_id,
                          'price_ticks':exact_units(r['price'],4),
                          'raw':{'account':ACCOUNT,'contract':SYMBOL,'quantity':1,
                                 'side':side,'order_id':order_id},
                          'broker_time':r['broker_time']}
            integer(normalized['price_ticks'],1)
            if exec_id in executions and executions[exec_id] != normalized:
                raise ValueError('execution_correction_requires_review')
            executions[exec_id] = normalized
        elif kind == 'commission':
            exec_id=r['execution_id']
            fee_record={k:r[k] for k in ('execution_id','currency','commission_and_fees')}
            if exec_id in commissions and commissions[exec_id] != fee_record:
                raise ValueError('commission_correction_requires_review')
            commissions[exec_id]=fee_record
        elif kind != 'summary':
            raise ValueError('unknown_snapshot_record')
    if seen_ends != ENDS:
        raise ValueError('callback_end_evidence_missing')
    for exec_id,execution in executions.items():
        fee=commissions.get(exec_id)
        execution['fee_cents']=None
        execution['fee_status']='MISSING'
        if fee is not None:
            try:
                if fee['currency'] != 'USD':raise ValueError('currency')
                execution['fee_cents']=exact_units(fee['commission_and_fees'],100)
                execution['fee_status']='KNOWN'
            except (ValueError,KeyError):
                execution['fee_status']='UNSUPPORTED_PRECISION_OR_CURRENCY'
    return {'status':'OBSERVED_FLAT','position':0,'owned_open_orders':[],
            'executions':list(executions.values()),'snapshot_is_atomic':False,
            'history_complete':False,'retry_authorized':False,
            'observed_through_ns':ended,
            'all_execution_fees_known':all(x['fee_cents'] is not None for x in executions.values())}
