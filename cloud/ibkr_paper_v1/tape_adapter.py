"""Strict adapter for the cloud recorder's receipt-time events.

Produces candidate replay input, never labels the IBKR tape exchange-complete.
Read in insertion order: sorting by timestamp would hide clock regressions.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json

from cloud.ibkr_paper_v1.execution import SYMBOL, NS, integer, canonical


def whole_size(value):
    if type(value) not in (str, int):
        raise ValueError('invalid_size_type')
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('invalid_size') from exc
    if not number.is_finite() or number < 1 or number != number.to_integral_value():
        raise ValueError('nonpositive_or_fractional_size')
    if number > 1_000_000_000:
        raise ValueError('implausible_size')
    return int(number)


def normalize(event_id, received_ns, kind, payload):
    integer(event_id, 1); integer(received_ns, 1)
    if kind not in ('quote', 'trade'):
        raise ValueError('not_market_data')
    if payload.get('contract') != SYMBOL:
        raise ValueError('wrong_contract')
    if type(payload.get('data_type')) is not int or payload['data_type'] != 1:
        raise ValueError('realtime_type_required')
    broker = integer(payload['broker_time_seconds'], 1)
    if not -NS <= received_ns - broker * NS <= 5 * NS:
        raise ValueError('broker_receipt_clock_mismatch')
    out = {'event_id': event_id, 'received_ns': received_ns, 'kind': kind,
           'contract': SYMBOL, 'data_type': 1, 'broker_time_seconds': broker}
    if kind == 'quote':
        bid = integer(payload['bid_ticks'], 1)
        ask = integer(payload['ask_ticks'], 1)
        if bid > ask:
            raise ValueError('crossed_quote')
        out.update(bid_ticks=bid, ask_ticks=ask,
                   bid_size=whole_size(payload['bid_size']),
                   ask_size=whole_size(payload['ask_size']))
    else:
        if (payload.get('unreported') is not False
                or payload.get('past_limit') is not False
                or payload.get('special_conditions') != ''
                or type(payload.get('tick_type')) is not int
                or payload['tick_type'] not in (1, 2)
                or payload.get('exchange') not in ('', 'CME')):
            raise ValueError('trade_eligibility_review_required')
        out.update(price_ticks=integer(payload['price_ticks'], 1),
                   size=whole_size(payload['size']), eligible=True,
                   exchange_label=payload['exchange'],
                   venue_basis='RECORDER_VERIFIED_CONTRACT')
    return out


class Tape:
    """One read-only, bounded interval within the caller's SQLite snapshot.

Metadata hashes the original rows as well as the normalized market events. The
caller must keep one database read transaction open across related intervals.
"""
    def __init__(self, db, start_ns, end_ns):
        integer(start_ns, 1); integer(end_ns, start_ns + 1)
        self.db, self.start, self.end = db, start_ns, end_ns
        self.used = False
        self.metadata = None

    def __iter__(self):
        if self.used:
            raise ValueError('tape_iterator_is_single_use')
        self.used = True
        digest = hashlib.sha256()
        previous = None
        counts = {'quote': 0, 'trade': 0, 'other': 0}
        rows = self.db.execute('SELECT id,received_ns,kind,payload FROM events '
                               'WHERE received_ns>=? AND received_ns<? ORDER BY id',
                               (self.start, self.end))
        for event_id, received, kind, raw in rows:
            key = (integer(received, 1), integer(event_id, 1))
            if previous is not None and (key[0] < previous[0] or key[1] <= previous[1]):
                raise ValueError('receipt_clock_or_id_regression')
            previous = key
            digest.update(canonical([event_id, received, kind, raw]).encode() + b'\n')
            payload = json.loads(raw)
            if (kind.startswith('invalid_') or kind == 'connection'
                    or (kind == 'broker_status' and payload.get('code') in (1100,1101,1102,1300,10197))
                    or (kind == 'health' and payload.get('status') != 'COLLECTING_REALTIME')):
                raise ValueError('recorded_feed_interruption_or_invalid_event')
            if kind in ('quote', 'trade'):
                counts[kind] += 1
                yield normalize(event_id, received, kind, payload)
            else:
                counts['other'] += 1
        self.metadata = {'source_sha256': digest.hexdigest(), 'counts': counts,
                         'start_ns': self.start, 'end_ns_exclusive': self.end,
                         'time_basis': 'LOCAL_RECEIPT_NS',
                         'strategy_evidence_approved': False}
