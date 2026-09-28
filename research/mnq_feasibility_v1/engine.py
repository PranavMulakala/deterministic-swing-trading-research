"""Offline, single-contract MNQ research. No network, broker, or credentials.

Prices are integer ticks; timestamps are integer nanoseconds. This models
historical top-of-book opportunities, not guaranteed or broker-observed fills.
"""
from bisect import bisect_left
from collections import Counter
from datetime import datetime, time
from math import ceil, floor, isfinite, sqrt
import re
from statistics import median
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
SECOND = 1_000_000_000
MINUTE = 60 * SECOND


def timestamp(day, hour, minute=0):
    return int(datetime.combine(datetime.fromisoformat(day).date(),
                                time(hour, minute), NY).timestamp()) * SECOND


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def validate(data):
    if data.get('schema_version') != 1 or data.get('evidence') not in ('SYNTHETIC', 'HISTORICAL'):
        raise ValueError('Expected schema_version=1 and explicit evidence label')
    if not data.get('source') or not data.get('time_basis'):
        raise ValueError('Source and timestamp basis are required')
    if data['time_basis'] != 'exchange_event_time':
        raise ValueError('Only exchange_event_time historical replay is implemented')
    sessions = data.get('sessions', [])
    days = [s['date'] for s in sessions]
    if days != sorted(set(days)):
        raise ValueError('Sessions must be unique and sorted, never silently reordered')
    for session in sessions:
        day = session['date']
        start, end = timestamp(day, 9, 30), timestamp(day, 16)
        contract = session['contract']
        if not isinstance(contract, str) or not re.fullmatch(r'MNQ[HMUZ][0-9]{1,4}', contract):
            raise ValueError('An actual dated MNQ contract is required, not a continuous series')
        if session.get('regular_session_complete') is not True:
            raise ValueError('Full regular-session coverage declaration required')
        if session.get('previous_date') and session['previous_date'] >= day:
            raise ValueError('Previous session must precede current session')
        last = (-1, -1)
        for event in session['events']:
            ts, seq = event['ts_ns'], event['seq']
            if not integer(ts) or not integer(seq) or not start <= ts < end:
                raise ValueError('Event outside 09:30-16:00 New York regular session')
            key = (ts, seq)
            if key <= last:
                raise ValueError('Duplicate or unordered event identity')
            last = key
            if event['type'] == 'trade':
                if not integer(event['price_ticks'], 1) or not integer(event['size'], 1):
                    raise ValueError('Trade prices/sizes must be positive integer ticks/contracts')
            elif event['type'] == 'quote':
                for name in ('bid_ticks', 'ask_ticks', 'bid_size', 'ask_size'):
                    if not integer(event[name]):
                        raise ValueError('Quote fields must be nonnegative integers')
            else:
                raise ValueError('Unknown event type')


def validate_config(cfg):
    # This version is deliberately one contract and MNQ only.
    if cfg['max_contracts'] != 1 or cfg['tick_size'] != .25 or cfg['tick_value'] != .5:
        raise ValueError('This engine supports one MNQ contract only')
    if cfg.get('orders_enabled') is not False or cfg.get('data_purchase_enabled') is not False:
        raise ValueError('Research-only configuration required')
    for key in ('initial_cash', 'risk_fraction', 'daily_loss_fraction', 'drawdown_fraction',
                'minimum_net_reward_risk'):
        v = cfg[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v <= 0:
            raise ValueError('Invalid positive configuration: ' + key)
    if any(cfg[k] >= 1 for k in ('risk_fraction', 'daily_loss_fraction', 'drawdown_fraction')):
        raise ValueError('Risk fractions must be below one')
    for key in ('max_entries_per_day', 'entry_delay_ns', 'entry_wait_ns', 'exit_delay_ns',
                'max_quote_gap_ns', 'max_spread_ticks', 'stop_buffer_ticks'):
        if not integer(cfg[key], 1):
            raise ValueError('Invalid integer configuration: ' + key)
    names = set()
    for s in cfg['scenarios']:
        if s['name'] in names:
            raise ValueError('Duplicate scenario name')
        names.add(s['name'])
        fee = s['round_trip_fee']
        if isinstance(fee, bool) or not isinstance(fee, (int, float)) or not isfinite(fee) or fee < 0:
            raise ValueError('Invalid fee')
        if not integer(s['slippage_ticks_per_side']):
            raise ValueError('Invalid slippage')
    if not names:
        raise ValueError('At least one cost scenario required')


def bars(session):
    """Causal per-minute trade OHLC and volume-weighted population variance."""
    start = timestamp(session['date'], 9, 30)
    by_minute = {}
    weight = mean = m2 = 0.0
    for t in session['events']:
        if t['type'] != 'trade':
            continue
        idx = (t['ts_ns'] - start) // MINUTE
        p, size = t['price_ticks'], t['size']
        total = weight + size
        delta = p - mean
        mean += delta * size / total
        m2 += size * delta * (p - mean)
        weight = total
        b = by_minute.setdefault(idx, {'open': p, 'high': p, 'low': p})
        b.update(high=max(b['high'], p), low=min(b['low'], p), close=p,
                 vwap=mean, sd=sqrt(max(0, m2 / weight)), end_ns=start + (idx + 1) * MINUTE)
    return by_minute


def signals(session, previous, cfg):
    if previous is None:
        return [], 'NO_PREVIOUS_SESSION'
    if previous['contract'] != session['contract']:
        return [], 'CONTRACT_CHANGED_NEEDS_SAME_CONTRACT_WARMUP'
    prior = bars(previous)
    if len(prior) != 390:
        return [], 'INCOMPLETE_PREVIOUS_SESSION_MINUTES'
    prior_high = max(b['high'] for b in prior.values())
    prior_low = min(b['low'] for b in prior.values())
    current = bars(session)
    result = []
    for i in range(120):  # confirmations strictly before 11:30, starting 09:45
        if i not in current:
            return result, 'MISSING_TRADE_MINUTE_HALT_REMAINING_SIGNALS'
        if i < 14:
            continue
        a, b = current[i - 1], current[i]
        direction = 0
        if (a['sd'] > 0 and a['close'] > a['vwap'] + 3 * a['sd']
                and a['low'] <= prior_high <= a['high'] and b['close'] < a['low']):
            direction = -1
        elif (a['sd'] > 0 and a['close'] < a['vwap'] - 3 * a['sd']
                and a['low'] <= prior_low <= a['high'] and b['close'] > a['high']):
            direction = 1
        if not direction or b['end_ns'] >= timestamp(session['date'], 11, 30):
            continue
        stop = (min(a['low'], b['low']) - cfg['stop_buffer_ticks'] if direction == 1
                else max(a['high'], b['high']) + cfg['stop_buffer_ticks'])
        target = floor(b['vwap']) if direction == 1 else ceil(b['vwap'])
        result.append({'id': f"{session['date']}:{i}:{direction}", 'day': session['date'],
                       'contract': session['contract'], 'signal_ns': b['end_ns'],
                       'direction': direction, 'stop_ticks': stop, 'target_ticks': target,
                       'vwap_ticks': b['vwap'], 'prior_high_ticks': prior_high,
                       'prior_low_ticks': prior_low})
    return result, None


def valid_quote(q):
    return 0 < q['bid_ticks'] <= q['ask_ticks'] and q['bid_size'] >= 1 and q['ask_size'] >= 1


def screen(signal, quotes, times, cfg, cost, budget):
    out = dict(signal, quote_index=None, planned_risk=None, risk_fits=None, eligible=False)
    due = signal['signal_ns'] + cfg['entry_delay_ns']
    idx = bisect_left(times, due)
    if idx == len(quotes) or times[idx] > due + cfg['entry_wait_ns']:
        return dict(out, reason='NO_TIMELY_QUOTE')
    q = quotes[idx]
    out.update(quote_index=idx, entry_ns=q['ts_ns'], bid_ticks=q['bid_ticks'],
               ask_ticks=q['ask_ticks'], spread_ticks=q['ask_ticks'] - q['bid_ticks'])
    if not valid_quote(q):
        return dict(out, reason='INVALID_OR_EMPTY_BOOK')
    if out['spread_ticks'] > cfg['max_spread_ticks']:
        return dict(out, reason='SPREAD_TOO_WIDE')
    direction, slip, fee = signal['direction'], cost['slippage_ticks_per_side'], cost['round_trip_fee']
    entry = q['ask_ticks'] + slip if direction == 1 else q['bid_ticks'] - slip
    stop_distance = direction * (entry - signal['stop_ticks'])
    target_distance = direction * (signal['target_ticks'] - entry)
    if stop_distance <= 0 or target_distance <= 0:
        return dict(out, reason='STOP_OR_TARGET_ALREADY_PASSED')
    risk = (stop_distance + slip) * cfg['tick_value'] + fee
    reward = (target_distance - slip) * cfg['tick_value'] - fee
    out.update(entry_ticks=entry, stop_distance_ticks=stop_distance,
               planned_risk=risk, planned_net_reward=reward, risk_fits=risk <= budget,
               net_reward_risk=reward / risk)
    if risk > budget:
        return dict(out, reason='RISK_BUDGET')
    if reward < cfg['minimum_net_reward_risk'] * risk:
        return dict(out, reason='NET_REWARD_TOO_SMALL')
    return dict(out, eligible=True, reason='ELIGIBLE')


def replay(data, cfg, cost, signal_override=None):
    """signal_override is for isolated fixture tests, never a CLI input."""
    cash = peak = cfg['initial_cash']
    maximum_dd = 0.0
    global_halt = None
    position = None
    decisions, trades, equity, session_notes, all_screens = [], [], [], [], []
    quality = []
    lookup = {s['date']: s for s in data['sessions']}
    fee, slip = cost['round_trip_fee'], cost['slippage_ticks_per_side']
    for session in data['sessions']:
        day = session['date']
        day_start, daily_halt, entries = cash, False, 0
        generated, note = signals(session, lookup.get(session.get('previous_date')), cfg)
        if signal_override is not None:
            generated = signal_override.get(day, [])
        session_notes.append({'date': day, 'signal_count': len(generated), 'note': note})
        quotes = [q for q in session['events'] if q['type'] == 'quote']
        times = [q['ts_ns'] for q in quotes]
        scheduled = {}
        for sig in generated:
            item = screen(sig, quotes, times, cfg, cost, cfg['initial_cash'] * cfg['risk_fraction'])
            all_screens.append(item)
            if item['quote_index'] is None:
                decisions.append(dict(item, portfolio_reason=item['reason']))
            else:
                scheduled.setdefault(item['quote_index'], []).append(item)
        last_valid = None

        def mark(q):
            nonlocal peak, maximum_dd, global_halt, daily_halt
            net = cash
            if position:
                liquidation = q['bid_ticks'] - slip if position['direction'] == 1 else q['ask_ticks'] + slip
                net += position['direction'] * (liquidation - position['entry_ticks']) * cfg['tick_value'] - fee / 2
            peak = max(peak, net)
            maximum_dd = max(maximum_dd, peak - net)
            if net <= day_start * (1 - cfg['daily_loss_fraction']):
                daily_halt = True
            if net <= peak * (1 - cfg['drawdown_fraction']):
                global_halt = global_halt or 'ACCOUNT_DRAWDOWN_PAUSE'
            equity.append({'day': day, 'ts_ns': q['ts_ns'], 'equity': round(net, 8),
                           'daily_halt': daily_halt, 'account_halt': global_halt})

        for idx, q in enumerate(quotes):
            if position and (not valid_quote(q) or (last_valid is not None and q['ts_ns'] - last_valid > cfg['max_quote_gap_ns'])):
                quality.append({'day': day, 'ts_ns': q['ts_ns'], 'reason': 'UNOBSERVED_OR_INVALID_BOOK_WHILE_EXPOSED'})
                global_halt = 'DATA_QUALITY_PAUSE'
            if valid_quote(q):
                last_valid = q['ts_ns']
                mark(q)
                if position:
                    direction = position['direction']
                    executable = q['bid_ticks'] if direction == 1 else q['ask_ticks']
                    reason = None
                    if position.get('exit_due_ns') is None:
                        if global_halt or daily_halt:
                            reason = global_halt or 'DAILY_LOSS_PAUSE'
                        elif direction * (executable - position['stop_ticks']) <= 0:
                            reason = 'STOP'
                        elif direction * (executable - position['target_ticks']) >= 0:
                            reason = 'TARGET'
                        elif q['ts_ns'] >= timestamp(day, 12):
                            reason = 'NOON_EXIT'
                        if reason:
                            position.update(exit_due_ns=q['ts_ns'] + cfg['exit_delay_ns'],
                                            exit_reason=reason, trigger_ns=q['ts_ns'])
                    elif q['ts_ns'] >= position['exit_due_ns']:
                        exit_price = executable - direction * slip
                        gross = direction * (exit_price - position['entry_ticks']) * cfg['tick_value']
                        cash += gross - fee / 2
                        trades.append(dict(position, exit_ns=q['ts_ns'], exit_ticks=exit_price,
                                           gross_pnl=gross, fees=fee, net_pnl=gross - fee))
                        position = None
                        mark(q)
            for item in scheduled.get(idx, []):
                reason = item['reason']
                if global_halt:
                    reason = global_halt
                elif daily_halt:
                    reason = 'DAILY_LOSS_PAUSE'
                elif position:
                    reason = 'POSITION_ALREADY_OPEN'
                elif entries >= cfg['max_entries_per_day']:
                    reason = 'DAILY_ENTRY_LIMIT'
                elif q['ts_ns'] >= timestamp(day, 11, 30):
                    reason = 'ENTRY_WINDOW_ENDED'
                elif item['planned_risk'] is not None:
                    # Re-evaluate against today's equity; do not let a fixed
                    # initial-capital screen override portfolio compounding.
                    if item['planned_risk'] > day_start * cfg['risk_fraction']:
                        reason = 'CURRENT_DAY_RISK_BUDGET'
                    elif item.get('net_reward_risk', 0) >= cfg['minimum_net_reward_risk']:
                        reason = 'ENTERED'
                if reason == 'ENTERED':
                    position = dict(item)
                    entries += 1
                    cash -= fee / 2
                    mark(q)
                decisions.append(dict(item, portfolio_reason=reason, day_risk_budget=day_start * cfg['risk_fraction']))
        if position:
            quality.append({'day': day, 'reason': 'UNRESOLVED_POSITION_AT_END_OF_AVAILABLE_QUOTES'})
            global_halt = 'UNRESOLVED_POSITION'
            break  # Never reset inventory overnight or invent a closing price.
    risk_known = [s for s in all_screens if s['planned_risk'] is not None]
    fits = sum(s['risk_fits'] is True for s in risk_known)
    count = len(all_screens)
    trustworthy = not quality and position is None
    net = sum(t['net_pnl'] for t in trades)
    distances = [s['stop_distance_ticks'] for s in risk_known]
    if position is None and abs(cfg['initial_cash'] + net - cash) > 1e-7:
        raise AssertionError('Cash and trade ledger disagree')
    return {'scenario': cost, 'pattern_signals': count, 'risk_assessable_signals': len(risk_known),
            'risk_unknown_signals': count - len(risk_known), 'risk_fit_signals': fits,
            'risk_fit_pct_of_all_patterns': fits / count * 100 if count else None,
            'risk_fit_pct_of_assessable': fits / len(risk_known) * 100 if risk_known else None,
            'entry_to_stop_ticks': {'minimum': min(distances), 'median': median(distances),
                                    'maximum': max(distances)} if distances else None,
            'eligible_after_risk_and_reward': sum(s['eligible'] for s in all_screens),
            'entries': sum(d['portfolio_reason'] == 'ENTERED' for d in decisions),
            'closed_trades': len(trades), 'closed_trade_net_pnl': net,
            'worst_closed_trade_net_pnl': min((t['net_pnl'] for t in trades), default=None),
            'ending_equity': cash if trustworthy else None,
            'max_observed_drawdown_dollars': maximum_dd,
            'full_drawdown_established': trustworthy,
            'account_halt': global_halt, 'quality_issues': quality,
            'unresolved_position': position, 'screens': all_screens, 'decisions': decisions,
            'rejection_counts': dict(Counter(d['portfolio_reason'] for d in decisions if d['portfolio_reason'] != 'ENTERED')),
            'trades': trades, 'equity': equity, 'session_notes': session_notes}


def analyze(data, cfg):
    validate(data)
    validate_config(cfg)
    return {'evidence': data['evidence'], 'status': 'SYNTHETIC_SOFTWARE_CHECK_ONLY' if data['evidence'] == 'SYNTHETIC'
            else 'HISTORICAL_DIAGNOSTIC_PENDING_DATA_AUDIT_AND_COST_VERIFICATION',
            'cost_status': cfg['cost_status'], 'source': data['source'],
            'limitations': ['Exchange-event clock, not local receipt or broker execution.',
                            'Declared input coverage is not independently verified vendor completeness.',
                            'Top-of-book size does not guarantee a fill; routing and queue competition unmodeled.',
                            'Fixed data/platform expenses and broker margin eligibility are not verified.',
                            'Quote gaps suppress final equity; observed drawdown is then only a lower bound.',
                            'Pilot outcomes cannot establish future profitability.'],
            'scenarios': [replay(data, cfg, s) for s in cfg['scenarios']]}
