"""Offline tests for test #21 on hand-built bars (rules, split-safe filters, selection files, trades, sizing, account)."""
import math
from pathlib import Path
import tempfile
import unittest

from research.stocks_in_play_orb_v1.backtest import account, pnl, size, trade_path
from research.stocks_in_play_orb_v1.data import calendar, metric_table, save, selections
from research.stocks_in_play_orb_v1.rules import daily_metrics, direction, in_play, relative_volume, tradeable


class RulesTest(unittest.TestCase):
    def test_universe_filters_are_strict_where_the_paper_says_so(self):
        self.assertTrue(tradeable(5.01, 1_000_000, 0.51))
        self.assertFalse(tradeable(5.00, 1_000_000, 0.51))          # price must be above $5
        self.assertFalse(tradeable(5.01, 999_999, 0.51))            # at least 1M shares a day
        self.assertFalse(tradeable(5.01, 1_000_000, 0.50))          # ATR above $0.50
        self.assertFalse(tradeable(5.01, float("nan"), 0.51))       # unknown history never qualifies

    def test_relative_volume_and_ranking(self):
        self.assertAlmostEqual(relative_volume(300, [100] * 14), 3.0)
        self.assertTrue(math.isnan(relative_volume(300, [100] * 13)))
        self.assertTrue(math.isnan(relative_volume(300, [0] * 14)))
        cands = [("BBB", 2.0), ("AAA", 2.0), ("CCC", 5.0), ("DDD", 0.99), ("EEE", float("nan")), ("FFF", 1.0)]
        self.assertEqual(in_play(cands), ["CCC", "AAA", "BBB", "FFF"])
        self.assertEqual(in_play(cands, n=2), ["CCC", "AAA"])

    def test_direction(self):
        self.assertEqual(direction([10, 11, 9, 10.5, 0]), 1)
        self.assertEqual(direction([10, 11, 9, 9.5, 0]), -1)
        self.assertEqual(direction([10, 11, 9, 10, 0]), 0)

    def test_split_does_not_fake_a_range_or_volume_jump(self):
        # $1 daily range and 2M shares a day in today's (post-split) units; a 2-for-1 split after day 20
        split = [[10, 10.5, 9.5, 10, 2e6] for _ in range(30)]
        raw = [[2 * o, 2 * h, 2 * l, 2 * c, v / 2] if k < 20 else [o, h, l, c, v] for k, (o, h, l, c, v) in enumerate(split)]
        m = daily_metrics(raw, split)
        self.assertTrue(math.isnan(m[14][1]))                       # needs 15 days of history
        vol, atr, f = m[19]
        self.assertAlmostEqual(f, 2.0)
        self.assertAlmostEqual(atr, 2.0)                            # in that day's pre-split dollars
        self.assertAlmostEqual(vol, 1e6)                            # in that day's pre-split shares
        vol, atr, f = m[20]
        self.assertAlmostEqual((vol, atr, f), (2e6, 1.0, 1.0))     # split day: no spike


class SelectionFilesTest(unittest.TestCase):
    """End to end through the saved-file layout: a split, a fetched-but-missing opening bar, an unfetched day."""

    def test_selection(self):
        days = [f"2024-01-{d:02d}" for d in range(2, 22)]           # 20 "trading days"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            save(base / "SPY_all.json.gz", {"date": days, "bars": [[1, 1, 1, 1, 1]] * 20})
            flat = [[20, 21, 19, 20, 3e6] for _ in days]
            save(base / "daily" / "AAA.json.gz", {"date": days, "split": flat,                 # 2-for-1 after day 10
                                                   "raw": [[2 * o, 2 * h, 2 * l, 2 * c, v / 2] if k < 10 else [o, h, l, c, v]
                                                           for k, (o, h, l, c, v) in enumerate(flat)]})
            for sym in ("BBB", "CCC", "DDD", "EEE"):
                save(base / "daily" / f"{sym}.json.gz", {"date": days, "split": flat, "raw": flat})
            for k, d in enumerate(days):
                bars = {"AAA": [40 if k < 10 else 20, 0, 0, 0, 50e3 if k < 10 else 100e3],   # 100k post-split shares
                        "BBB": [20, 0, 0, 0, 100e3], "DDD": [20, 0, 0, 0, 100e3], "EEE": [4.99, 0, 0, 0, 900e3]}
                requested = ["AAA", "BBB", "CCC", "DDD", "EEE"]
                if k == 17:
                    bars = {"AAA": [20, 21, 19, 20.5, 300e3], "BBB": [20, 21, 19, 19.5, 200e3],
                            "CCC": [20, 21, 19, 20.5, 150e3], "DDD": [20, 21, 19, 20.5, 900e3], "EEE": [4.99, 5, 4, 5, 900e3]}
                elif k == 10:
                    requested = ["AAA", "BBB", "CCC", "EEE"]          # DDD not fetched that day: unknown history
                    del bars["DDD"]
                if k < 17 and k % 2:
                    bars["CCC"] = [20, 0, 0, 0, 100e3]               # CCC fetched daily; no 9:30 bar on even days
                save(base / "open5" / f"{d}.json.gz", {"requested": requested, "bars": bars})
            cal = calendar(base)
            table = metric_table(base, ["AAA", "BBB", "CCC", "DDD", "EEE"], cal)
            picks = selections(base, table, cal, 20, days[17])
            got = [(s, round(rv, 3)) for s, rv, _, _, _ in picks[days[17]]]
            # AAA 300k vs 100k (pre-split 50k x 2); CCC 150k vs 7 x 100k / 14; BBB 200k / 100k; DDD unknown; EEE $4.99
            self.assertEqual(got, [("AAA", 3.0), ("CCC", 3.0), ("BBB", 2.0)])
            self.assertAlmostEqual(picks[days[17]][0][3], 2.0)      # ATR in that day's dollars


class TradeTest(unittest.TestCase):
    FIRST_UP = [10.0, 10.5, 9.9, 10.4, 1e5]                         # long; stop 10% x ATR 2 = 0.20

    def test_mid_bar_entry_with_ambiguous_stop(self):
        later = [[575, 10.3, 10.6, 10.25, 10.55, 0], [580, 10.55, 10.9, 10.5, 10.8, 0], [955, 10.8, 11, 10.7, 10.95, 0]]
        main = trade_path(self.FIRST_UP, later, 2.0, 1, "stop")
        self.assertEqual((main["entry"], round(main["exit"], 6), main["reason"], main["ambiguous"]),
                         (10.5, 10.3, "stop_same_bar", True))
        flip = trade_path(self.FIRST_UP, later, 2.0, 1, "flip")
        self.assertEqual((flip["entry"], flip["exit"], flip["exit_m"], flip["reason"]), (10.5, 10.95, 955, "close"))

    def test_gap_fill_at_the_open_makes_the_same_bar_stop_certain(self):
        later = [[575, 10.7, 10.8, 10.45, 10.6, 0], [955, 10.6, 10.7, 10.5, 10.6, 0]]
        for mode in ("stop", "flip"):
            t = trade_path(self.FIRST_UP, later, 2.0, 1, mode)
            self.assertEqual((t["entry"], round(t["exit"], 6), t["ambiguous"]), (10.7, 10.5, False))

    def test_close_past_the_stop_is_certain_and_later_gaps_fill_at_the_open(self):
        t = trade_path(self.FIRST_UP, [[575, 10.4, 10.6, 10.2, 10.25, 0], [955, 10, 10, 10, 10, 0]], 2.0, 1, "flip")
        self.assertEqual((t["reason"], round(t["exit"], 6)), ("stop_same_bar", 10.3))
        t = trade_path(self.FIRST_UP, [[575, 10.4, 10.6, 10.4, 10.55, 0], [580, 10.1, 10.2, 10.0, 10.1, 0]], 2.0, 1)
        self.assertEqual((t["reason"], t["exit"], t["exit_m"]), ("stop", 10.1, 580))

    def test_no_entry_and_short_side(self):
        self.assertIsNone(trade_path(self.FIRST_UP, [[575, 10.4, 10.45, 10.3, 10.4, 0]], 2.0, 1))
        first_down = [10.0, 10.1, 9.5, 9.6, 1e5]
        later = [[575, 9.6, 9.58, 9.45, 9.5, 0], [580, 9.5, 9.55, 9.3, 9.35, 0], [955, 9.3, 9.4, 9.1, 9.2, 0]]
        t = trade_path(first_down, later, 1.0, -1)
        self.assertEqual((t["entry"], round(t["stop"], 6), t["exit"], t["reason"]), (9.5, 9.6, 9.2, "close"))
        up = [[575, 9.6, 9.58, 9.45, 9.5, 0], [580, 9.5, 9.7, 9.5, 9.65, 0]]
        self.assertEqual(round(trade_path(first_down, up, 1.0, -1)["exit"], 6), 9.6)


class AccountTest(unittest.TestCase):
    def test_sizing_costs_and_daily_compounding(self):
        self.assertEqual(size(100_000, 2.0, 50.0, 0.05), 100)       # cap: $5,000 / $50 (risk alone: 5,000 shares)
        self.assertEqual(size(100_000, 50.0, 10.0, 0.05), 200)      # risk: $1,000 / $5 stop distance
        long = {"side": 1, "entry": 10.0, "exit": 11.0}
        self.assertAlmostEqual(pnl(long, 100), 100 * (11 * 0.9999 - 10 * 1.0001) - 0.7)
        short = {"side": -1, "entry": 10.0, "exit": 9.0}
        self.assertAlmostEqual(pnl(short, 100), -100 * (9 * 1.0001 - 10 * 0.9999) - 0.7)
        t = {"side": 1, "entry": 10.0, "stop": 9.8, "exit": 11.0, "entry_m": 580, "exit_m": 955, "reason": "close",
             "ambiguous": False}
        s = {**t, "side": -1}
        plan = {"2024-01-02": [("AAA", 2.0, 3.0, t, t), ("BBB", 2.0, 2.0, s, s)], "2024-01-03": [("AAA", 2.0, 3.0, t, t)]}
        trades, curve, small = account(["2024-01-02", "2024-01-03"], plan, ("2024-01-01", "2024-12-31"))
        self.assertEqual([x["symbol"] for x in trades], ["AAA", "AAA"])                    # the short is skipped
        self.assertEqual(trades[0]["shares"], 500)                   # $5,000 cap / $10
        day1 = 100_000 + pnl(t, 500)
        self.assertAlmostEqual(curve[0][1], day1)
        self.assertEqual(trades[1]["shares"], math.floor(0.05 * day1 / 10))                # sized on the new equity
        self.assertEqual(small, 0)
        both, _, _ = account(["2024-01-02"], plan, ("2024-01-01", "2024-12-31"), sides=(1, -1))
        self.assertEqual(len(both), 2)


if __name__ == "__main__":
    unittest.main()
