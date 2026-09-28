"""Streaming, bounded-memory coverage audit; never promotes data to trading evidence.

Uses local receipt time, not invented exchange nanoseconds. Silence can be a quiet
market or a feed failure: either fails the frozen one-second quote-gap criterion.
"""
import json
from collections import Counter

SECOND = 1_000_000_000
MINUTE = 60 * SECOND


def audit_session(db, day, start, end, now):
    lo, hi = int(start.timestamp())*SECOND, int(end.timestamp())*SECOND
    counts, minutes, issues = Counter(), set(), set()
    first = last = None
    max_gap = 0
    # Account for receipt-time discontinuities without sorting them away.
    prior_receipt = None
    for received, kind, raw in db.execute(
            'SELECT received_ns,kind,payload FROM events WHERE received_ns>=? '
            'AND received_ns<? ORDER BY id', (lo, hi)):
        counts[kind] += 1
        if prior_receipt is not None and received < prior_receipt:
            issues.add('RECEIPT_CLOCK_MOVED_BACKWARD')
        prior_receipt = received
        payload = json.loads(raw)
        if kind in ('quote','trade'):
            if payload.get('data_type') != 1:
                issues.add('REALTIME_TYPE_MISSING_OR_INVALID')
            broker = payload.get('broker_time_seconds')
            if type(broker) is not int or not -SECOND <= received-broker*SECOND <= 5*SECOND:
                issues.add('BROKER_RECEIPT_CLOCK_MISMATCH')
            if payload.get('contract') != 'MNQZ6':
                issues.add('WRONG_CONTRACT')
        if kind == 'quote':
            if first is None: first = received
            if last is not None: max_gap = max(max_gap,received-last)
            last = received
        elif kind == 'trade':
            # AllLast includes trades requiring eligibility review. Don't silently
            # include them in a claimed canonical VWAP series.
            if (payload.get('unreported') or payload.get('past_limit')
                    or payload.get('special_conditions') or payload.get('tick_type') not in (1,2)):
                issues.add('TRADE_ELIGIBILITY_REVIEW_REQUIRED')
            else:
                minutes.add((received-lo)//MINUTE)
        elif kind.startswith('invalid_'):
            issues.add('INVALID_MARKET_EVENT')
        elif kind == 'broker_status' and payload.get('code') in (1100,1101,1102,1300,10197):
            issues.add('BROKER_SESSION_INTERRUPTION')
        elif kind == 'connection':
            issues.add('CONNECTED_DURING_SESSION')
        elif kind == 'health' and payload.get('status') != 'COLLECTING_REALTIME':
            issues.add('UNHEALTHY_INTERVAL')
    finished = now >= end
    expected = (hi-lo)//MINUTE
    if expected != 390: issues.add('SHORT_SESSION_EXCLUDED')
    if first is None or first-lo > SECOND: issues.add('OPENING_QUOTES_MISSING')
    if finished and (last is None or hi-last > SECOND): issues.add('CLOSING_QUOTES_MISSING')
    if max_gap > SECOND: issues.add('QUOTE_GAP_OVER_ONE_SECOND')
    if finished and len(minutes) != expected: issues.add('MISSING_TRADE_MINUTES')
    if not finished: issues.add('SESSION_NOT_FINISHED')
    return {'date':day, 'status':'INCOMPLETE_OR_REVIEW_REQUIRED' if issues else 'OBSERVATION_CHECKS_PASSED',
            'issues':sorted(issues), 'counts':dict(counts), 'trade_minutes':len(minutes),
            'expected_minutes':expected, 'max_quote_gap_seconds':max_gap/SECOND,
            'first_quote_receipt_ns':first, 'last_quote_receipt_ns':last,
            'strategy_evidence_approved':False, 'broker_execution_evidence':False,
            'time_basis':'LOCAL_RECEIPT_NS_WITH_BROKER_SECONDS'}


if __name__ == '__main__':
    import argparse
    import sqlite3
    from pathlib import Path
    from cloud.ibkr_paper_v1.operations import calendar_rows, session_for, utcnow, NY
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',default='/var/lib/ibkr-paper')
    parser.add_argument('--references',default='/var/lib/ibkr-paper/references')
    args=parser.parse_args()
    now=utcnow()
    rows=calendar_rows(args.references,now)
    session=session_for(rows,now)
    if session:
        db=sqlite3.connect((Path(args.state)/'state.sqlite').as_uri()+'?mode=ro',uri=True)
        print(json.dumps(audit_session(db,now.astimezone(NY).date().isoformat(),*session,now),indent=2))
        db.close()
    else:
        print(json.dumps({'status':'NO_RESEARCH_SESSION_TODAY','strategy_evidence_approved':False}))
