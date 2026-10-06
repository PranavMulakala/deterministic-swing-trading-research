"""Offline tests for test #17 on hand-built daily prices."""
from datetime import date, timedelta
import unittest

from research.momentum_lite_like_v1.backtest import (FILL, START_CASH, metrics_at, period_returns, picks_at, prepare,
                                                     simulate, stats)


def weekdays(start, end):
    out, d = [], date.fromisoformat(start)
    while d.isoformat() <= end:
        if d.weekday() < 5 and d.strftime("%m-%d") != "01-01":     # New Year's Day is a market holiday
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


DAYS = weekdays("2019-01-02", "2020-03-31")


def path(up, down, start=10.0):
    """Alternating daily moves; open = previous close; volume keeps dollar volume at $1B."""
    closes, p = [], start
    for k in range(len(DAYS)):
        p *= (1 + up) if k % 2 == 0 else (1 - down)
        closes.append(p)
    opens = [start] + closes[:-1]
    return prepare({"date": list(DAYS), "open": opens, "high": [max(o, c) for o, c in zip(opens, closes)],
                    "low": [min(o, c) for o, c in zip(opens, closes)], "close": closes,
                    "volume": [1e9 / c for c in closes]})


def flat(level=100.0):
    n = len(DAYS)
    return prepare({"date": list(DAYS), "open": [level] * n, "high": [level] * n, "low": [level] * n,
                    "close": [level] * n, "volume": [1e7] * n})


class RuleTest(unittest.TestCase):
    def setUp(self):
        self.stocks = {"AAA": path(0.06, 0.04), "BBB": path(0.005, 0.005), "CCC": path(0.04, 0.06)}

    def test_metrics_and_eligibility(self):
        i = DAYS.index("2019-12-31")
        dvol, move, ret = metrics_at(self.stocks["AAA"], i)
        self.assertAlmostEqual(dvol, 1e9)
        self.assertAlmostEqual(move, 0.05)                       # (6% + 4%) / 2
        self.assertGreater(ret, 0)
        self.assertLess(metrics_at(self.stocks["BBB"], i)[1], 0.04)   # calm: not LITE-like
        self.assertIsNone(metrics_at(self.stocks["AAA"], 100))   # not enough history for 6 months

    def test_picks_need_positive_momentum_and_fill(self):
        self.assertEqual([s for s, _ in picks_at(self.stocks, "2019-12-31", n=2)], ["AAA"])
        loose = [s for s, _ in picks_at(self.stocks, "2019-12-31", n=2, need_positive=False)]
        self.assertEqual(loose, ["AAA", "CCC"])                  # strongest first; CCC only without the filter

    def test_trades_at_next_open_with_costs(self):
        allp = {**self.stocks, FILL: flat()}
        curve, log = simulate(self.stocks, allp, DAYS, "2020-01-02", "2020-03-31", n=2)
        self.assertEqual([e["day"] for e in log], ["2020-01-02", "2020-02-03", "2020-03-02"])
        first = log[0]
        self.assertEqual(first["formation"], "2019-12-31")
        self.assertEqual([p[0] for p in first["picks"]], ["AAA"])
        self.assertEqual(first["smh_weight"], 0.5)
        self.assertAlmostEqual(first["fee"], 0.001 * (START_CASH - 100.0), places=6)   # second pass trades 99,900
        a = allp["AAA"]
        i = a["_idx"]["2020-01-02"]
        q_a = 0.5 * (START_CASH - 100.0) / a["open"][i]
        q_s = 0.5 * (START_CASH - 100.0) / 100.0
        cash = START_CASH - first["fee"] - (q_a * a["open"][i] + q_s * 100.0)
        self.assertAlmostEqual(curve[0][1], cash + q_a * a["close"][i] + q_s * 100.0, places=6)
        self.assertGreater(log[1]["turnover"], 0)                # drift is rebalanced back to 50/50

    def test_stats_and_periods(self):
        curve = [("2020-01-02", 100_000.0), ("2020-06-01", 50_000.0), ("2022-12-30", 120_000.0), ("2023-01-03", 132_000.0)]
        s = stats(curve)
        self.assertEqual(s["max_drawdown_pct"], -50.0)
        self.assertEqual(period_returns(curve, (("a", "2020-01-01", "2022-12-31"), ("b", "2023-01-01", "2026-12-31"))),
                         {"a": 20.0, "b": 10.0})


if __name__ == "__main__":
    unittest.main()
