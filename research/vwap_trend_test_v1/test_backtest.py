"""Offline tests for test #30 (the strict VWAP-trend rule) on hand-built 5-minute bars.

  PYTHONPATH=src:. .venv/bin/python -m unittest research.vwap_trend_test_v1.test_backtest   (pytest also collects it)
"""
from datetime import datetime, timezone
import math
import unittest
from zoneinfo import ZoneInfo

from research.vwap_trend_test_v1.backtest import (Ind, account, conditions, ema_series, placebo, prepare, rule_trades,
                                                  summarize, wilder_atr)

NY = ZoneInfo("America/New_York")
DAY = "2020-01-06"
WIN = ("2020-01-01", "2020-12-31")
ALIGNED_LONG = dict(c=101.0, vw=(100.0, 100.0, 100.0), e=(100.5, 100.0, 99.5, 99.0))
ALIGNED_SHORT = dict(c=99.0, vw=(100.0, 100.0, 100.0), e=(99.5, 100.0, 100.5, 101.0))
NOT_ALIGNED = dict(c=100.0, vw=(100.0, 100.0, 100.0), e=(99.0, 99.5, 100.5, 101.0))


def raw_row(d, hh, mm, v, vw, px=None):
    t = datetime.fromisoformat(f"{d}T{hh:02d}:{mm:02d}:00").replace(tzinfo=NY).astimezone(timezone.utc)
    p = vw if px is None else px
    return {"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "o": p, "h": p, "l": p, "c": p, "v": v, "vw": vw, "n": 1}


def build(spec):
    """spec: list of dicts {d, m, o, h, l, c, vw: (session, pd, overnight), e: (e20, e50, e100, e200), atr}."""
    days = {}
    for i, b in enumerate(spec):
        a, _ = days.get(b["d"], (i, i))
        days[b["d"]] = (a, i + 1)
    ind = Ind(date=[b["d"] for b in spec], m=[b["m"] for b in spec], o=[b["o"] for b in spec],
              h=[b["h"] for b in spec], l=[b["l"] for b in spec], c=[b["c"] for b in spec],
              ema={n: [b["e"][k] for b in spec] for k, n in enumerate((20, 50, 100, 200))},
              atr=[b.get("atr", 1.0) for b in spec], svwap=[b["vw"][0] for b in spec],
              pdvwap=[b["vw"][1] for b in spec], onvwap=[b["vw"][2] for b in spec], days=days)
    ind.cond = {s: conditions(ind, s) for s in (1, -1)}
    return ind


def day_spec(d=DAY, state=None, bars=None, last=955):
    """A full day 9:30..`last` of flat bars at 100.5 (high 100.8, low 100.2), NOT aligned by default.
    state: {minute: ALIGNED_* dict} sets the trend state from that minute until the next entry.
    bars: {minute: (o, h, l, c)} overrides prices (indicator state still from `state`)."""
    state, bars, out, cur = state or {}, bars or {}, [], NOT_ALIGNED
    for m in range(570, last + 5, 5):
        cur = state.get(m, cur)
        o, h, l, c = bars.get(m, (100.5, 100.8, 100.2, cur["c"]))
        out.append({"d": d, "m": m, "o": o, "h": h, "l": l, "c": c, "vw": cur["vw"], "e": cur["e"], "atr": 1.0})
    return out


def trades_of(spec, side=1, **kw):
    return rule_trades(build(spec), side, WIN, warmup=0, **kw)


class IndicatorArithmetic(unittest.TestCase):
    def setUp(self):
        rows = [raw_row("2020-01-02", 8, 0, 100, 10.0),            # Thu pre-market -> Thu overnight
                raw_row("2020-01-02", 9, 30, 100, 10.0), raw_row("2020-01-02", 9, 35, 300, 14.0),
                raw_row("2020-01-02", 16, 5, 200, 20.0),           # Thu after-hours -> Fri overnight
                raw_row("2020-01-03", 7, 0, 200, 30.0),            # Fri pre-market -> Fri overnight
                raw_row("2020-01-03", 9, 30, 100, 17.0), raw_row("2020-01-03", 9, 35, 100, 19.0),
                raw_row("2020-01-03", 19, 55, 100, 50.0),          # Fri after-hours -> Mon overnight
                raw_row("2020-01-04", 8, 0, 100, 40.0),            # Saturday bar -> Mon overnight
                raw_row("2020-01-06", 9, 30, 100, 60.0),
                raw_row("2020-01-07", 9, 30, 100, 61.0)]           # Tue: no extended-hours volume at all
        self.ind = prepare(list(reversed(rows)))                   # input order must not matter

    def test_regular_session_split(self):
        self.assertEqual(self.ind.m, [570, 575, 570, 575, 570, 570])
        self.assertEqual(list(self.ind.days), ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"])

    def test_session_vwap(self):
        self.assertAlmostEqual(self.ind.svwap[0], 10.0)
        self.assertAlmostEqual(self.ind.svwap[1], (10 * 100 + 14 * 300) / 400)          # 13
        self.assertAlmostEqual(self.ind.svwap[3], (17 * 100 + 19 * 100) / 200)          # 18, resets each day

    def test_previous_day_vwap(self):
        self.assertIsNone(self.ind.pdvwap[0])                                           # no previous day in data
        self.assertAlmostEqual(self.ind.pdvwap[2], (1000 + 4200 + 1700) / 500)          # 13.8
        self.assertAlmostEqual(self.ind.pdvwap[3], (1000 + 4200 + 1700 + 1900) / 600)
        self.assertAlmostEqual(self.ind.pdvwap[4], (1700 + 1900 + 6000) / 300)          # anchored at Fri 9:30 only

    def test_overnight_vwap(self):
        self.assertAlmostEqual(self.ind.onvwap[0], 10.0)
        self.assertAlmostEqual(self.ind.onvwap[2], (20 * 200 + 30 * 200) / 400)         # 25, fixed for the day
        self.assertAlmostEqual(self.ind.onvwap[3], 25.0)
        self.assertAlmostEqual(self.ind.onvwap[4], (50 * 100 + 40 * 100) / 200)         # weekend bar included
        self.assertIsNone(self.ind.onvwap[5])                                           # no volume -> no level
        self.assertFalse(self.ind.cond[1][5] or self.ind.cond[-1][5])                  # -> no trades that day

    def test_ema_seed_and_wilder_atr(self):
        e = ema_series([1.0, 2.0, 3.0, 4.0], 2)
        self.assertIsNone(e[0])
        for got, want in zip(e[1:], (1.5, 2.5, 3.5)):
            self.assertAlmostEqual(got, want)
        a = wilder_atr([2.0, 3.0, 5.0], [1.0, 2.0, 3.0], [1.5, 2.5, 4.0], n=2)
        self.assertIsNone(a[0])
        self.assertAlmostEqual(a[1], 1.25)          # mean of TR 1 and 1.5 (|3 - prev close 1.5|)
        self.assertAlmostEqual(a[2], 1.875)         # (1.25 + TR 2.5) / 2


class Triggers(unittest.TestCase):
    def test_fresh_alignment_triggers_next_bar_open(self):
        t = trades_of(day_spec(state={600: ALIGNED_LONG}, bars={605: (101.0, 101.2, 100.8, 101.0)}))
        self.assertEqual(len(t), 1)
        ind_m = {i: m for i, m in enumerate(range(570, 960, 5))}
        self.assertEqual((ind_m[t[0]["signal"]], ind_m[t[0]["e"]]), (600, 605))
        self.assertEqual((t[0]["entry"], t[0]["stop"], t[0]["target"]), (101.0, 99.5, 104.0))

    def test_already_aligned_does_not_trigger(self):
        self.assertEqual(trades_of(day_spec(state={570: ALIGNED_LONG})), [])

    def test_each_condition_is_required(self):
        broken = [dict(ALIGNED_LONG, vw=(101.5, 100, 100)), dict(ALIGNED_LONG, vw=(100, 101.5, 100)),
                  dict(ALIGNED_LONG, vw=(100, 100, 101.5)), dict(ALIGNED_LONG, e=(101.5, 100, 99.5, 99)),
                  dict(ALIGNED_LONG, e=(100.5, 99.0, 99.5, 98))]
        for st in broken:
            self.assertEqual(trades_of(day_spec(state={600: st})), [], st)

    def test_signal_window_9_45_to_15_00(self):
        self.assertEqual(trades_of(day_spec(state={580: ALIGNED_LONG})), [])                    # 9:40: skipped
        self.assertEqual(trades_of(day_spec(state={905: ALIGNED_LONG})), [])                    # 15:05: skipped
        self.assertEqual(len(trades_of(day_spec(state={585: ALIGNED_LONG}))), 1)                # 9:45 boundary
        self.assertEqual(len(trades_of(day_spec(state={900: ALIGNED_LONG}))), 1)                # 15:00 boundary

    def test_warmup_blocks_early_signals(self):
        self.assertEqual(rule_trades(build(day_spec(state={600: ALIGNED_LONG})), 1, WIN), [])  # 200-bar default

    def test_bounce_variant(self):
        touch = day_spec(state={570: ALIGNED_LONG}, bars={600: (100.6, 101.2, 99.9, 101.0)})  # low 99.9 <= VWAP 100
        self.assertEqual(trades_of(touch), [])                                                 # no fresh alignment
        self.assertEqual(len(trades_of(touch, trigger="bounce")), 1)
        no_touch = day_spec(state={570: ALIGNED_LONG}, bars={m: (100.6, 101.2, 100.1, 101.0) for m in range(570, 960, 5)})
        self.assertEqual(trades_of(no_touch, trigger="bounce"), [])


class Exits(unittest.TestCase):
    def one(self, bars, **kw):
        base = {605: (101.0, 101.2, 100.8, 101.0)}                    # entry bar: open 101, stop 99.5, target 104
        base.update(bars)
        t = trades_of(day_spec(state={600: ALIGNED_LONG}, bars=base), **kw)
        self.assertGreaterEqual(len(t), 1)          # a bar closing below VWAP and recovering can re-trigger later
        return t[0]

    def test_stop(self):
        t = self.one({615: (100.5, 100.6, 99.4, 99.6)})
        self.assertEqual((t["reason"], t["exit"]), ("stop", 99.5))

    def test_target(self):
        t = self.one({615: (102.5, 104.1, 102.4, 103.9)})
        self.assertEqual((t["reason"], t["exit"]), ("target", 104.0))

    def test_stop_on_the_entry_bar(self):
        t = self.one({605: (101.0, 101.2, 99.4, 99.8)})
        self.assertEqual((t["reason"], t["exit"], t["x"]), ("stop", 99.5, t["e"]))

    def test_same_bar_touch_assumes_stop(self):
        t = self.one({615: (101.0, 104.1, 99.4, 101.0)})
        self.assertEqual((t["reason"], t["exit"], t["ambiguous"]), ("stop_same_bar", 99.5, True))
        t = self.one({615: (101.0, 104.1, 99.4, 101.0)}, same_bar="target")
        self.assertEqual((t["reason"], t["exit"]), ("target_same_bar", 104.0))

    def test_gap_through_levels_fills_at_open(self):
        t = self.one({615: (99.0, 99.2, 98.5, 99.1)})
        self.assertEqual((t["reason"], t["exit"]), ("stop_gap", 99.0))
        t = self.one({615: (104.5, 105.0, 104.2, 104.8)})
        self.assertEqual((t["reason"], t["exit"]), ("target_gap", 104.5))

    def test_exit_at_1555_close(self):
        t = self.one({955: (100.6, 100.9, 100.3, 100.7)})
        ind = build(day_spec())
        self.assertEqual((t["reason"], t["exit"], ind.m[t["x"]]), ("close", 100.7, 955))

    def test_signal_at_the_last_bar_cannot_enter(self):
        self.assertEqual(trades_of(day_spec(state={900: ALIGNED_LONG}, last=900)), [])         # no next bar that day


class Positions(unittest.TestCase):
    def test_one_position_at_a_time(self):
        state = {600: ALIGNED_LONG, 605: NOT_ALIGNED, 610: ALIGNED_LONG,      # 2nd fresh alignment while in a trade
                 615: NOT_ALIGNED, 630: ALIGNED_LONG}                          # 3rd: after the stop at 620
        bars = {605: (101.0, 101.2, 100.8, 101.0), 620: (100.5, 100.6, 99.4, 99.6), 635: (101.0, 101.2, 100.8, 101.0)}
        t = trades_of(day_spec(state=state, bars=bars))
        m = list(range(570, 960, 5))
        self.assertEqual([(m[x["signal"]], m[x["e"]], x["reason"]) for x in t], [(600, 605, "stop"), (630, 635, "close")])

    def test_signal_at_the_exit_bar_enters_next_bar(self):
        state = {600: ALIGNED_LONG, 605: NOT_ALIGNED, 620: ALIGNED_LONG}
        bars = {605: (101.0, 101.2, 100.8, 101.0), 620: (100.5, 100.6, 99.4, 101.0)}     # stopped, then realigns
        m = list(range(570, 960, 5))
        t = trades_of(day_spec(state=state, bars=bars))
        self.assertEqual([(m[x["signal"]], m[x["x"]]) for x in t][:2], [(600, 620), (620, 955)])

    def test_account_sizing_costs_and_counts(self):
        bars = {605: (101.0, 101.2, 100.8, 101.0), 615: (102.5, 104.1, 102.4, 103.9)}
        ind = build(day_spec(state={600: ALIGNED_LONG}, bars=bars))
        raw = rule_trades(ind, 1, WIN, warmup=0)
        trades, curve = account(raw, ind, 1, WIN, slip=0.0001)
        fill, sell = 101.0 * 1.0001, 104.0 * 0.9999
        shares = math.floor(min(1000 / (fill - 99.5), 100_000 / fill))
        self.assertEqual(trades[0]["shares"], shares)
        self.assertAlmostEqual(trades[0]["pnl"], shares * (sell - fill))
        self.assertAlmostEqual(curve[-1][1], 100_000 + shares * (sell - fill))
        self.assertAlmostEqual(trades[0]["qqq_points"], 3.0)
        with self.assertRaises(AssertionError):                       # entered must equal recorded
            account(raw + [dict(raw[0], date="2021-01-04")], ind, 1, WIN)
        with self.assertRaises(AssertionError):                       # overlapping positions are refused
            account(raw + [dict(raw[0])], ind, 1, WIN)
        s = summarize(trades, curve, "main")
        self.assertEqual((s["trades"], s["exit_split"]["target"], s["break_even_target_hit_rate_pct_before_costs"]),
                         (1, 1, 33.3))


class MirroredShort(unittest.TestCase):
    def test_short_is_the_mirror(self):
        bars = {m: (99.0, 99.2, 98.8, 99.0) for m in range(605, 960, 5)}                 # quiet bars after entry
        bars[615] = (97.0, 97.2, 95.9, 96.1)                                             # target 99 - 3 = 96
        ind = build(day_spec(state={600: ALIGNED_SHORT}, bars=bars))
        self.assertEqual(rule_trades(ind, 1, WIN, warmup=0), [])                        # not a long setup
        raw = rule_trades(ind, -1, WIN, warmup=0)
        trades, _ = account(raw, ind, -1, WIN, slip=0.0)
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t["side"], t["entry"], t["stop"], t["target"], t["exit"], t["reason"]),
                         ("short", 99.0, 100.5, 96.0, 96.0, "target"))
        self.assertEqual(t["shares"], math.floor(min(1000 / 1.5, 100_000 / 99.0)))
        self.assertAlmostEqual(t["pnl"], t["shares"] * 3.0)
        self.assertAlmostEqual(t["qqq_points"], 3.0)                                     # points in trade direction

    def test_short_stop_and_slippage_direction(self):
        bars = {m: (99.0, 99.2, 98.8, 99.0) for m in range(605, 960, 5)}
        bars[615] = (99.5, 100.6, 99.4, 100.4)                                           # stop 100.5
        ind = build(day_spec(state={600: ALIGNED_SHORT}, bars=bars))
        trades, _ = account(rule_trades(ind, -1, WIN, warmup=0), ind, -1, WIN, slip=0.0001)
        t = trades[0]
        self.assertEqual((t["reason"], t["exit"]), ("stop", 100.5))
        self.assertAlmostEqual(t["pnl"], t["shares"] * (99.0 * 0.9999 - 100.5 * 1.0001))  # sell lower, buy back higher


class Placebo(unittest.TestCase):
    def test_random_entries_match_count_and_never_overlap(self):
        spec = sum((day_spec(d=d) for d in ("2020-01-06", "2020-01-07", "2020-01-08")), [])
        ind = build(spec)
        res = placebo(ind, [{"date": "2020-01-06"}] * 3, window=WIN, repeats=3, warmup=0)
        self.assertEqual([r["trades"] for r in res["runs"]], [3, 3, 3])              # flat days: 1 trade per day
        again = placebo(ind, [{"date": "2020-01-06"}] * 3, window=WIN, repeats=3, warmup=0)
        self.assertEqual(res["runs"], again["runs"])                                  # seeded, reproducible


if __name__ == "__main__":
    unittest.main()
