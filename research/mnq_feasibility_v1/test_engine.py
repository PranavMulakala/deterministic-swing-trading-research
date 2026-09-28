import copy
import json
from pathlib import Path
import unittest

from .engine import SECOND, analyze, bars, replay, screen, signals, timestamp, validate, validate_config
from .fixture import dataset
from .run import budget_table

CFG = json.loads((Path(__file__).parent / 'config.json').read_text())
DAY = '2026-09-04'
T = timestamp(DAY, 10)


def quote(seconds, bid, ask=None):
    return dict(type='quote', ts_ns=T + int(seconds * SECOND), seq=int(seconds * 1000),
                bid_ticks=bid, ask_ticks=bid + 1 if ask is None else ask, bid_size=1, ask_size=1)


def signal(direction=1, ts=T-SECOND, stop=90, target=130, identifier='first'):
    return dict(id=identifier, day=DAY, contract='MNQU6', signal_ns=ts,
                direction=direction, stop_ticks=stop, target_ticks=target)


def tape(quotes, day=DAY):
    return dict(schema_version=1, evidence='SYNTHETIC', source='test', time_basis='exchange_event_time',
                sessions=[dict(date=day, previous_date=None, contract='MNQU6',
                               regular_session_complete=True, events=quotes)])


class FeasibilityTests(unittest.TestCase):
    def test_tick_budget_ladder(self):
        self.assertEqual([r['max_quote_to_stop_ticks'] for r in budget_table(CFG)], [21, 19, 17, 13])

    def test_50_tick_stop_exceeds_budget(self):
        q = [quote(0, 100)]
        r = screen(signal(stop=51), q, [T], CFG, CFG['scenarios'][0], 12.5)
        self.assertEqual(r['planned_risk'], 27)
        self.assertEqual(r['reason'], 'RISK_BUDGET')

    def test_long_ask_short_bid_and_both_slippage_sides(self):
        cost = CFG['scenarios'][1]
        q = [quote(0, 100)]
        a = screen(signal(), q, [T], CFG, cost, 12.5)
        b = screen(signal(-1, stop=111, target=70), q, [T], CFG, cost, 12.5)
        self.assertEqual((a['entry_ticks'], b['entry_ticks']), (102, 99))
        self.assertEqual(a['planned_risk'], 8.5)
        self.assertEqual(b['planned_risk'], 8.5)

    def test_first_quote_rejected_without_cherry_picking(self):
        q = [quote(0, 100, 110), quote(.5, 100)]
        r = screen(signal(), q, [x['ts_ns'] for x in q], CFG, CFG['scenarios'][0], 12.5)
        self.assertEqual(r['reason'], 'SPREAD_TOO_WIDE')

    def test_missing_quote_is_unknown_not_zero_risk(self):
        r = screen(signal(), [], [], CFG, CFG['scenarios'][0], 12.5)
        self.assertIsNone(r['risk_fits'])
        self.assertIsNone(r['planned_risk'])

    def test_entry_delay_and_timeout(self):
        q = [quote(-.1, 100), quote(2, 101)]
        r = screen(signal(), q, [x['ts_ns'] for x in q], CFG, CFG['scenarios'][0], 12.5)
        self.assertEqual(r['reason'], 'NO_TIMELY_QUOTE')

    def test_latency_can_turn_target_touch_into_loss(self):
        q = [quote(0, 100), quote(.2, 130), quote(.4, 80)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal()]})
        self.assertEqual(r['trades'][0]['exit_reason'], 'TARGET')
        self.assertEqual(r['trades'][0]['net_pnl'], -12.5)
        self.assertEqual(r['ending_equity'], 4987.5)

    def test_gap_through_stop_is_not_filled_at_stop(self):
        q = [quote(0, 100), quote(.2, 89), quote(.4, 70)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal()]})
        self.assertEqual(r['trades'][0]['exit_ticks'], 70)
        self.assertLess(r['trades'][0]['net_pnl'], -r['trades'][0]['planned_risk'])

    def test_short_exit_buys_at_ask(self):
        q = [quote(0, 100), quote(.2, 69), quote(.4, 68)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal(-1, stop=111, target=70)]})
        self.assertEqual(r['trades'][0]['exit_ticks'], 69)
        self.assertEqual(r['closed_trade_net_pnl'], 13.5)

    def test_quote_gap_nulls_equity_and_latches_pause(self):
        q = [quote(0, 100), quote(2, 101), quote(2.2, 100)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal()]})
        self.assertIsNone(r['ending_equity'])
        self.assertFalse(r['full_drawdown_established'])
        self.assertEqual(r['account_halt'], 'DATA_QUALITY_PAUSE')

    def test_unresolved_position_not_reset_to_cash(self):
        r = replay(tape([quote(0, 100)]), CFG, CFG['scenarios'][0], {DAY: [signal()]})
        self.assertIsNotNone(r['unresolved_position'])
        self.assertIsNone(r['ending_equity'])

    def test_daily_marked_loss_blocks_new_entry(self):
        q = [quote(0, 100), quote(.2, 40), quote(.4, 40), quote(.6, 100)]
        second = signal(ts=T-int(.4*SECOND), identifier='second')
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal(), second]})
        self.assertEqual(r['entries'], 1)
        self.assertEqual(r['decisions'][-1]['portfolio_reason'], 'DAILY_LOSS_PAUSE')

    def test_drawdown_pause_persists_to_next_day(self):
        cfg = copy.deepcopy(CFG)
        cfg['drawdown_fraction'] = .005  # small fixture threshold, not production tuning
        q = [quote(0, 100), quote(.2, 40), quote(.4, 40)]
        data = tape(q)
        next_day = '2026-09-08'
        offset = timestamp(next_day, 10) - T
        next_q = [dict(e, ts_ns=e['ts_ns'] + offset) for e in [quote(0, 100), quote(.2, 130), quote(.4, 130)]]
        data['sessions'] += tape(next_q, next_day)['sessions']
        next_sig = dict(signal(), day=next_day, signal_ns=T-SECOND+offset, id='next')
        r = replay(data, cfg, cfg['scenarios'][0], {DAY: [signal()], next_day: [next_sig]})
        self.assertEqual(r['entries'], 1)
        self.assertEqual(r['account_halt'], 'ACCOUNT_DRAWDOWN_PAUSE')

    def test_one_position_no_scaling(self):
        q = [quote(0, 100), quote(.2, 101), quote(.4, 130), quote(.6, 130)]
        second = signal(ts=T-int(.8*SECOND), identifier='second')
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [signal(), second]})
        self.assertEqual(r['entries'], 1)
        self.assertEqual(r['decisions'][1]['portfolio_reason'], 'POSITION_ALREADY_OPEN')

    def test_two_entries_limit(self):
        q = [quote(0, 100), quote(.2, 130), quote(.4, 130),
             quote(.6, 100), quote(.8, 130), quote(1, 130), quote(1.2, 100)]
        sigs = [signal(ts=T-SECOND+int(x*SECOND), identifier=str(x)) for x in (0, .6, 1.2)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: sigs})
        self.assertEqual(r['entries'], 2)
        self.assertEqual(r['closed_trades'], 2)
        self.assertEqual(r['decisions'][-1]['portfolio_reason'], 'DAILY_ENTRY_LIMIT')

    def test_drawdown_uses_unrealized_peak(self):
        cfg = copy.deepcopy(CFG)
        cfg['drawdown_fraction'] = .005
        q = [quote(0, 100), quote(.2, 200), quote(.4, 100), quote(.6, 100)]
        r = replay(tape(q), cfg, cfg['scenarios'][0], {DAY: [signal(target=1000)]})
        self.assertEqual(r['account_halt'], 'ACCOUNT_DRAWDOWN_PAUSE')
        self.assertEqual(r['max_observed_drawdown_dollars'], 50)
        self.assertEqual(r['closed_trade_net_pnl'], -2.5)

    def test_noon_exit_has_latency(self):
        noon = timestamp(DAY, 12)
        # Enter inside the normal window with continuous quotes through noon.
        start = timestamp(DAY, 11, 29)
        q = [dict(quote(0, 100), ts_ns=start+i*SECOND, seq=i) for i in range(1861)]
        q += [dict(quote(0, 103), ts_ns=noon+int(.2*SECOND), seq=1861)]
        sig = signal(ts=start-SECOND, target=1000)
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [sig]})
        self.assertEqual(r['trades'][0]['exit_reason'], 'NOON_EXIT')
        self.assertEqual(r['trades'][0]['exit_ns'], noon+int(.2*SECOND))

    def test_daily_pause_resets_but_smaller_day_risk_budget_applies(self):
        q = [quote(0, 100), quote(.2, 40), quote(.4, 40)]
        data = tape(q)
        next_day = '2026-09-08'
        offset = timestamp(next_day, 10) - T
        next_q = [dict(e, ts_ns=e['ts_ns']+offset) for e in [quote(0, 100), quote(.2, 130), quote(.4, 130)]]
        data['sessions'] += tape(next_q, next_day)['sessions']
        next_sig = dict(signal(stop=80), day=next_day, signal_ns=T-SECOND+offset, id='next')
        # This next trade needs exactly $12.50, which no longer fits the smaller account.
        r = replay(data, CFG, CFG['scenarios'][0], {DAY: [signal()], next_day: [next_sig]})
        self.assertEqual(r['decisions'][-1]['portfolio_reason'], 'CURRENT_DAY_RISK_BUDGET')
        self.assertLess(r['decisions'][-1]['day_risk_budget'], 12.5)
        self.assertIsNone(r['account_halt'])

    def test_mirrored_short_pattern(self):
        data = dataset()
        for session in data['sessions']:
            for e in session['events']:
                if e['type'] == 'trade':
                    e['price_ticks'] = 80000 - e['price_ticks']
                else:
                    e['bid_ticks'], e['ask_ticks'] = 80000-e['ask_ticks'], 80000-e['bid_ticks']
        found, _ = signals(data['sessions'][1], data['sessions'][0], CFG)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['direction'], -1)
        r = analyze(data, CFG)['scenarios'][0]
        self.assertEqual(r['closed_trades'], 1)
        self.assertEqual(r['ending_equity'], 5000+r['closed_trade_net_pnl'])

    def test_missing_quote_stays_in_all_signal_denominator(self):
        first = signal()
        missing = signal(ts=T+100*SECOND, identifier='missing')
        q = [quote(0, 100), quote(.2, 130), quote(.4, 130)]
        r = replay(tape(q), CFG, CFG['scenarios'][0], {DAY: [first, missing]})
        self.assertEqual(r['risk_fit_pct_of_all_patterns'], 50)
        self.assertEqual(r['risk_fit_pct_of_assessable'], 100)
        self.assertEqual(r['risk_unknown_signals'], 1)

    def test_full_signal_pipeline_on_invented_tape(self):
        r = analyze(dataset(), CFG)
        self.assertEqual(r['status'], 'SYNTHETIC_SOFTWARE_CHECK_ONLY')
        first = r['scenarios'][0]
        self.assertEqual(first['pattern_signals'], 1)
        self.assertEqual(first['entries'], 1)
        self.assertEqual(first['closed_trades'], 1)
        self.assertEqual(first['ending_equity'], 5000 + first['closed_trade_net_pnl'])

    def test_future_trade_cannot_change_earlier_signal(self):
        data = dataset()
        a, _ = signals(data['sessions'][1], data['sessions'][0], CFG)
        later = data['sessions'][1]['events'][-1]
        self.assertEqual(later['type'], 'trade')
        later['price_ticks'] = 999999
        b, _ = signals(data['sessions'][1], data['sessions'][0], CFG)
        self.assertEqual(a, b)

    def test_missing_minute_halts_only_later_signals(self):
        data = dataset()
        current = data['sessions'][1]
        missing_ts = timestamp(DAY, 10, 1) + SECOND
        current['events'] = [e for e in current['events'] if e['ts_ns'] != missing_ts]
        found, reason = signals(current, data['sessions'][0], CFG)
        self.assertEqual(len(found), 1)
        self.assertEqual(reason, 'MISSING_TRADE_MINUTE_HALT_REMAINING_SIGNALS')

    def test_previous_day_and_contract_are_required(self):
        data = dataset()
        self.assertEqual(signals(data['sessions'][1], None, CFG)[1], 'NO_PREVIOUS_SESSION')
        data['sessions'][0]['contract'] = 'MNQM6'
        self.assertIn('CONTRACT_CHANGED', signals(data['sessions'][1], data['sessions'][0], CFG)[1])

    def test_volume_weighted_variance(self):
        d = tape([])['sessions'][0]
        d['events'] = [dict(type='trade', ts_ns=timestamp(DAY, 9, 30)+SECOND, price_ticks=100, size=1),
                       dict(type='trade', ts_ns=timestamp(DAY, 9, 30)+2*SECOND, price_ticks=104, size=3)]
        b = bars(d)[0]
        self.assertEqual(b['vwap'], 103)
        self.assertAlmostEqual(b['sd'] ** 2, 3)

    def test_duplicate_unordered_and_mixed_symbol_rejected(self):
        d = dataset()
        d['sessions'][0]['events'].insert(1, dict(d['sessions'][0]['events'][0]))
        with self.assertRaises(ValueError):
            validate(d)
        d = dataset()
        d['sessions'][1]['contract'] = 'NQU6'
        with self.assertRaises(ValueError):
            validate(d)

    def test_no_silent_real_label_or_incomplete_session(self):
        d = dataset()
        d['evidence'] = 'REAL_PROFIT'
        with self.assertRaises(ValueError):
            validate(d)
        d = dataset()
        d['sessions'][1]['regular_session_complete'] = False
        with self.assertRaises(ValueError):
            validate(d)

    def test_nan_costs_and_wrong_multiplier_rejected(self):
        cfg = copy.deepcopy(CFG)
        cfg['scenarios'][0]['round_trip_fee'] = float('nan')
        with self.assertRaises(ValueError):
            validate_config(cfg)
        cfg = copy.deepcopy(CFG)
        cfg['tick_value'] = 5
        with self.assertRaises(ValueError):
            validate_config(cfg)

    def test_zero_signals_not_a_success_rate(self):
        r = analyze(tape([]), CFG)['scenarios'][0]
        self.assertIsNone(r['risk_fit_pct_of_all_patterns'])


if __name__ == '__main__':
    unittest.main()
