"""Same portfolio rules as engine.replay, with indexed quotes and flat-period skips.

Every quote while exposed is evaluated. Flat equity marks are omitted; decisions,
trades, pauses, P&L, and drawdown are compared with the unchanged reference engine.
"""
from bisect import bisect_left
from collections import Counter
from statistics import median

from engine import screen, timestamp, valid_quote


def replay(sessions, cfg, cost):
    cash = peak = cfg['initial_cash']
    maximum_dd = 0.0
    global_halt = None
    position = None
    decisions, trades, equity, notes, all_screens, quality = [], [], [], [], [], []
    fee, slip = cost['round_trip_fee'], cost['slippage_ticks_per_side']
    for session in sessions:
        day = session['date']
        day_start, daily_halt, entries = cash, False, 0
        generated = session['signals']
        notes.append(dict(date=day,signal_count=len(generated),note=session['note']))
        quotes, times = session['quotes'], session['times']
        scheduled = {}
        for sig in generated:
            item = screen(sig, quotes, times, cfg, cost, cfg['initial_cash'] * cfg['risk_fraction'])
            all_screens.append(item)
            if item['quote_index'] is None:
                decisions.append(dict(item,portfolio_reason=item['reason']))
            else:
                scheduled.setdefault(item['quote_index'],[]).append(item)
        decision_indexes = sorted(scheduled)
        last_valid = None

        def mark(q):
            nonlocal peak, maximum_dd, global_halt, daily_halt
            net = cash
            if position:
                liquidation = q['bid_ticks'] - slip if position['direction'] == 1 else q['ask_ticks'] + slip
                net += position['direction'] * (liquidation - position['entry_ticks']) * cfg['tick_value'] - fee / 2
            peak = max(peak,net)
            maximum_dd = max(maximum_dd,peak-net)
            if net <= day_start * (1-cfg['daily_loss_fraction']):daily_halt=True
            if net <= peak * (1-cfg['drawdown_fraction']):global_halt=global_halt or 'ACCOUNT_DRAWDOWN_PAUSE'
            equity.append(dict(day=day,ts_ns=q['ts_ns'],equity=round(net,8),daily_halt=daily_halt,account_halt=global_halt))

        idx = 0
        while idx < len(quotes):
            if position is None:
                cursor = bisect_left(decision_indexes,idx)
                if cursor == len(decision_indexes):break
                next_idx = decision_indexes[cursor]
                # No equity can change while flat; retain the actual most recent valid
                # quote so entry does not create an artificial data-gap pause.
                if next_idx > idx:
                    prior = next_idx-1
                    while prior >= idx:
                        q0=quotes[prior]
                        if valid_quote(q0):
                            last_valid=q0['ts_ns'];break
                        prior-=1
                idx=next_idx
            q=quotes[idx]
            if position and (not valid_quote(q) or (last_valid is not None and q['ts_ns']-last_valid>cfg['max_quote_gap_ns'])):
                quality.append(dict(day=day,ts_ns=q['ts_ns'],reason='UNOBSERVED_OR_INVALID_BOOK_WHILE_EXPOSED'))
                global_halt='DATA_QUALITY_PAUSE'
            if valid_quote(q):
                last_valid=q['ts_ns'];mark(q)
                if position:
                    direction=position['direction']
                    executable=q['bid_ticks'] if direction==1 else q['ask_ticks']
                    reason=None
                    if position.get('exit_due_ns') is None:
                        if global_halt or daily_halt:reason=global_halt or 'DAILY_LOSS_PAUSE'
                        elif direction*(executable-position['stop_ticks'])<=0:reason='STOP'
                        elif direction*(executable-position['target_ticks'])>=0:reason='TARGET'
                        elif q['ts_ns']>=timestamp(day,12):reason='NOON_EXIT'
                        if reason:position.update(exit_due_ns=q['ts_ns']+cfg['exit_delay_ns'],exit_reason=reason,trigger_ns=q['ts_ns'])
                    elif q['ts_ns']>=position['exit_due_ns']:
                        exit_price=executable-direction*slip
                        gross=direction*(exit_price-position['entry_ticks'])*cfg['tick_value']
                        cash+=gross-fee/2
                        trades.append(dict(position,exit_ns=q['ts_ns'],exit_ticks=exit_price,gross_pnl=gross,fees=fee,net_pnl=gross-fee))
                        position=None;mark(q)
            for item in scheduled.get(idx,[]):
                reason=item['reason']
                if global_halt:reason=global_halt
                elif daily_halt:reason='DAILY_LOSS_PAUSE'
                elif position:reason='POSITION_ALREADY_OPEN'
                elif entries>=cfg['max_entries_per_day']:reason='DAILY_ENTRY_LIMIT'
                elif q['ts_ns']>=timestamp(day,11,30):reason='ENTRY_WINDOW_ENDED'
                elif item['planned_risk'] is not None:
                    if item['planned_risk']>day_start*cfg['risk_fraction']:reason='CURRENT_DAY_RISK_BUDGET'
                    elif item.get('net_reward_risk',0)>=cfg['minimum_net_reward_risk']:reason='ENTERED'
                if reason=='ENTERED':
                    position=dict(item);entries+=1;cash-=fee/2;mark(q)
                decisions.append(dict(item,portfolio_reason=reason,day_risk_budget=day_start*cfg['risk_fraction']))
            idx+=1
        if position:
            quality.append(dict(day=day,reason='UNRESOLVED_POSITION_AT_END_OF_AVAILABLE_QUOTES'))
            global_halt='UNRESOLVED_POSITION';break
    known=[s for s in all_screens if s['planned_risk'] is not None]
    fits=sum(s['risk_fits'] is True for s in known)
    count=len(all_screens)
    trustworthy=not quality and position is None
    net=sum(t['net_pnl'] for t in trades)
    distances=[s['stop_distance_ticks'] for s in known]
    if position is None and abs(cfg['initial_cash']+net-cash)>1e-7:raise AssertionError('Cash reconciliation failed')
    return dict(scenario=cost,pattern_signals=count,risk_assessable_signals=len(known),risk_unknown_signals=count-len(known),
        risk_fit_signals=fits,risk_fit_pct_of_all_patterns=fits/count*100 if count else None,
        risk_fit_pct_of_assessable=fits/len(known)*100 if known else None,
        entry_to_stop_ticks=dict(minimum=min(distances),median=median(distances),maximum=max(distances)) if distances else None,
        eligible_after_risk_and_reward=sum(s['eligible'] for s in all_screens),entries=sum(d['portfolio_reason']=='ENTERED' for d in decisions),
        closed_trades=len(trades),closed_trade_net_pnl=net,worst_closed_trade_net_pnl=min((t['net_pnl'] for t in trades),default=None),
        ending_equity=cash if trustworthy else None,max_observed_drawdown_dollars=maximum_dd,full_drawdown_established=trustworthy,
        account_halt=global_halt,quality_issues=quality,unresolved_position=position,screens=all_screens,decisions=decisions,
        rejection_counts=dict(Counter(d['portfolio_reason'] for d in decisions if d['portfolio_reason']!='ENTERED')),
        trades=trades,equity=equity,session_notes=notes)
