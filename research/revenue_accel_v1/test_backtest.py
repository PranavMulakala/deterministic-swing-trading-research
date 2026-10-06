"""Offline tests for test #20 on hand-built revenue and prices."""
from datetime import date, timedelta
import unittest

from research.revenue_accel_v1.backtest import (FILL, START_CASH, company_tickers, picks_at, prepare, ranked,
                                                simulate)
from research.revenue_accel_v1.fetch_frames import CONCEPTS
from research.revenue_accel_v1.revenue import fingerprint, flagged, prev_label, quarterly

RFC, REV = CONCEPTS[0], CONCEPTS[1]


def weekdays(start, end):
    out, d = [], date.fromisoformat(start)
    while d.isoformat() <= end:
        if d.weekday() < 5 and d.strftime("%m-%d") != "01-01":
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


DAYS = weekdays("2019-06-03", "2020-03-31")


def bars(close=10.0, dollar_volume=50e6, step=0.0):
    closes = [close * (1 + step) ** k for k in range(len(DAYS))]
    opens = [close] + closes[:-1]
    return prepare({"date": list(DAYS), "open": opens, "high": [max(o, c) for o, c in zip(opens, closes)],
                    "low": [min(o, c) for o, c in zip(opens, closes)], "close": closes,
                    "volume": [dollar_volume / c for c in closes]})


def calendar_quarters(values, first="2018Q1"):
    """One tag's series from consecutive calendar-quarter revenues: {label: (quarter end, value)}."""
    out, lab = {}, first
    for v in values:
        y, q = int(lab[:4]), int(lab[5])
        end = (date(y + (q == 4), 1 if q == 4 else 3 * q + 1, 1) - timedelta(days=1)).isoformat()
        out[lab] = (end, v)
        lab = prev_label(lab, -1)
    return out


def one_tag(values, first="2018Q1"):
    return [calendar_quarters(values, first)] + [{} for _ in CONCEPTS[1:]]


class RevenueTest(unittest.TestCase):
    def test_june_fiscal_year_fourth_quarter_is_derived(self):
        # LITE-style year: Jul 2023 - Jun 2024; three quarters tagged, the Apr-Jun quarter only inside the annual total
        frames = {RFC: {"q": {7: [("2023Q3", "2023-07-02", "2023-09-30", 100.0), ("2023Q4", "2023-10-01", "2023-12-30", 110.0),
                                  ("2024Q1", "2023-12-31", "2024-03-30", 120.0)]},
                        "y": {7: [("2023-07-02", "2024-06-29", 480.0)]}}}
        series = quarterly(frames)[7][0]
        self.assertEqual(series["2024Q2"], ("2024-06-29", 150.0))
        self.assertEqual(series["2023Q3"], ("2023-09-30", 100.0))

    def test_growth_uses_one_tag_per_comparison(self):
        # the preferred tag has only recent quarters; growth must not mix it with the other tag's year-ago values
        rev = calendar_quarters([100, 100, 100, 100, 100, 100, 100, 100, 110, 125, 150])        # 2018Q1..2020Q3
        rfc = {k: v for k, v in calendar_quarters([10] * 8 + [11, 12.5, 15]).items() if k >= "2020Q1"}
        fp = fingerprint([rfc, rev, {}, {}], "2021-01-29")                # 2020Q3 (ended Sep 30) is known
        self.assertEqual(fp[0], 150)                                     # size from the tag used for the growth
        self.assertAlmostEqual(fp[1], 0.50)
        self.assertAlmostEqual(fp[2], 0.25)
        self.assertAlmostEqual(fp[3], 0.10)

    def test_ninety_day_lag_and_stale_quarters(self):
        series = one_tag([100] * 8 + [110, 125, 150])                     # 2018Q1..2020Q3
        self.assertAlmostEqual(fingerprint(series, "2020-12-28")[1], 0.25)   # 89 days after Sep 30: still 2020Q2
        self.assertAlmostEqual(fingerprint(series, "2020-12-29")[1], 0.50)   # 90 days: 2020Q3 counts
        self.assertIsNotNone(fingerprint(series, "2021-04-15"))           # 197 days old: still current
        self.assertIsNone(fingerprint(series, "2021-04-20"))              # 202 days old: the company stopped reporting

    def test_flag_rules(self):
        self.assertTrue(flagged((60e6, 0.50, 0.25, 0.10)))
        self.assertFalse(flagged((40e6, 0.50, 0.25, 0.10)))               # too small
        self.assertFalse(flagged((60e6, 0.24, 0.10, 0.05)))               # not fast enough
        self.assertFalse(flagged((60e6, 0.50, 0.45, 0.10)))               # sped up by only 5 points
        self.assertFalse(flagged((60e6, 0.50, 0.25, 0.30)))               # the quarter before had slowed down
        self.assertTrue(flagged((60e6, 0.50, 0.45, 0.60), need_accel=False))
        self.assertFalse(flagged(None))

    def test_class_share_tickers_and_first_listing(self):
        rows = {"0": {"cik_str": 1, "ticker": "BRK-B"}, "1": {"cik_str": 1, "ticker": "BRK-A"},
                "2": {"cik_str": 2, "ticker": "ZZZ"}, "10": {"cik_str": 3, "ticker": "AAA"}}
        self.assertEqual(company_tickers({"BRK.A", "BRK.B", "AAA"}, rows), {1: "BRK.B", 3: "AAA"})


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        self.stocks = {"AAA": bars(step=0.01), "BBB": bars(), "CCC": bars(dollar_volume=5e6), "DDD": bars()}
        self.tickers = {1: "AAA", 2: "BBB", 3: "CCC", 4: "DDD"}
        base = [100e6] * 4                                                # 2018; then 2019 Q1-Q3 below
        self.quarters = {1: one_tag(base + [110e6, 125e6, 150e6]),        # growth 10/25/50%: sped up 25 points
                         2: one_tag(base + [110e6, 140e6, 200e6]),        # 10/40/100%: sped up 60 points
                         3: one_tag(base + [110e6, 140e6, 200e6]),        # the same, but too little dollar volume
                         4: one_tag(base + [140e6, 135e6, 130e6])}        # 40/35/30%: fast but slowing

    def test_ranking_by_speed_up_with_liquidity_filter(self):
        top, n = picks_at("2019-12-31", self.stocks, self.quarters, self.tickers, n=20)
        self.assertEqual([t for t, _, _ in top], ["BBB", "AAA"])
        self.assertEqual(n, 2)
        self.assertAlmostEqual(top[0][1], 0.60)
        loose = ranked("2019-12-31", self.stocks, self.quarters, self.tickers, need_accel=False)
        self.assertEqual([t for t, _, _ in loose], ["BBB", "AAA", "DDD"])   # by growth itself: 100%, 50%, 30%

    def test_empty_slots_go_to_spy_and_trades_happen_at_the_next_open(self):
        allp = {**self.stocks, FILL: bars(close=100.0)}
        choose = lambda day: picks_at(day, self.stocks, self.quarters, self.tickers, n=4)
        curve, log = simulate(allp, DAYS, "2020-01-02", "2020-03-31", choose, n=4)
        self.assertEqual([e["day"] for e in log], ["2020-01-02", "2020-02-03", "2020-03-02"])
        first = log[0]
        self.assertEqual(first["formation"], "2019-12-31")
        self.assertEqual([p[0] for p in first["picks"]], ["BBB", "AAA"])
        self.assertEqual(first["spy_weight"], 0.5)
        self.assertAlmostEqual(first["fee"], 0.001 * (START_CASH - 100.0), places=6)   # second pass trades 99,900
        net, i = START_CASH - 100.0, DAYS.index("2020-01-02")
        q = {"AAA": 0.25 * net / allp["AAA"]["open"][i], "BBB": 0.25 * net / allp["BBB"]["open"][i],
             FILL: 0.5 * net / allp[FILL]["open"][i]}
        cash = START_CASH - first["fee"] - net
        self.assertAlmostEqual(curve[0][1], cash + sum(q[s] * allp[s]["close"][i] for s in q), places=6)
        self.assertNotEqual(allp["AAA"]["open"][i], allp["AAA"]["close"][i])   # so the open/close timing is tested
        self.assertGreater(log[1]["turnover"], 0)                         # AAA's drift is rebalanced back


if __name__ == "__main__":
    unittest.main()
