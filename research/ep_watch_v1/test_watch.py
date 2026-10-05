"""Offline tests for the EP forward watch, including an end-to-end evening run on fake data that must match the
test #16 backtest code exactly."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from zoneinfo import ZoneInfo

from research.ep_test_v1 import backtest as bt
from research.ep_test_v1.candidates import candidate_days
from research.ep_watch_v1 import watch

NY = ZoneInfo("America/New_York")


def weekdays(start, n):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


DAYS = weekdays("2026-01-05", 80)
EVENT, OTHER, TODAY = DAYS[62], DAYS[64], DAYS[70]


def series(closes, highs=None, lows=None, opens=None, vols=None, days=DAYS):
    n = len(closes)
    return {"date": days[:n], "open": opens or list(closes), "high": highs or [c + 1 for c in closes],
            "low": lows or [c - 1 for c in closes], "close": list(closes), "volume": vols or [1e6] * n}


def stock(event_day):
    """$50 flat (1M shares/day, 4% daily range) until a +12% gap on event_day, then a steady rise."""
    k = DAYS.index(event_day)
    closes = [50.0] * k + [57.8] + [58.0 + i for i in range(len(DAYS) - k - 1)]
    opens = [50.0] * k + [56.0] + [c - 0.5 for c in closes[k + 1:]]
    highs = [51.0] * k + [58.0] + [c + 0.5 for c in closes[k + 1:]]
    lows = [49.0] * k + [55.0] + [c - 1.0 for c in closes[k + 1:]]
    vols = [1e6] * k + [3e6] + [1.5e6] * (len(DAYS) - k - 1)
    return series(closes, highs, lows, opens, vols)


EVENT_BARS = [[570, 56.0, 57.0, 55.0, 56.5, 1.2e6], [600, 56.5, 56.9, 55.5, 56.6, 3e5],
              [630, 56.8, 57.5, 56.2, 57.3, 2e5], [700, 57.3, 58.0, 56.5, 57.8, 2e5]]


def alpaca_rows(b):
    return [{"t": f"{d}T04:00:00Z", "o": o, "h": h, "l": l, "c": c, "v": v}
            for d, o, h, l, c, v in zip(b["date"], b["open"], b["high"], b["low"], b["close"], b["volume"])]


def to_utc(day, minute):
    t = datetime.fromisoformat(f"{day}T{minute // 60:02d}:{minute % 60:02d}:00").replace(tzinfo=NY)
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeApi:
    def __init__(self):
        spy = series([400.0 + 0.1 * i for i in range(len(DAYS))])
        self.daily = {"AAA": stock(EVENT), "BBB": stock(OTHER), "SPY": spy}
        flat = [[m, 400.0, 400.5, 399.5, 400.0, 1e6] for m in range(570, 960, 5)]
        self.intraday = {("AAA", EVENT): EVENT_BARS, ("BBB", OTHER): EVENT_BARS}
        self.intraday.update({("SPY", d): flat for d in DAYS})

    def trading_days(self, start, end):
        return [d for d in DAYS if start <= d <= end]

    def bars(self, symbols, timeframe, start, end):
        out = {}
        for s in symbols:
            if timeframe == "1Day" and s in self.daily:
                rows = [r for r in alpaca_rows(self.daily[s]) if start <= r["t"] <= end]
            else:
                day = start[:10]
                for d in DAYS:                      # the ET day whose session the UTC window covers
                    if to_utc(d, 570) <= start <= to_utc(d, 955) or start == to_utc(d, 570):
                        day = d
                rows = [{"t": to_utc(day, x[0]), "o": x[1], "h": x[2], "l": x[3], "c": x[4], "v": x[5]}
                        for x in self.intraday.get((s, day), []) if start <= to_utc(day, x[0]) < end]
            if rows:
                out[s] = rows
        return out


class FakeSec:
    def rows(self, symbol):
        if symbol == "AAA":                           # earnings 8-K the evening before the gap
            prev = DAYS[DAYS.index(EVENT) - 1]
            return [[f"{prev}T21:05:00.000Z", prev, "2.02,9.01"]]
        return [] if symbol == "BBB" else None


class PieceTest(unittest.TestCase):
    def test_gap_candidates_match_the_backtest_superset(self):
        b = stock(EVENT)
        self.assertEqual(watch.gap_candidates({"AAA": b}, DAYS), {d: ["AAA"] for d in candidate_days(b)})
        self.assertEqual(candidate_days(b), [EVENT])

    def test_morning_row_statuses(self):
        b = series([50.0] * 30, highs=[51.0] * 30, lows=[49.0] * 30)
        acc = bt.acceptance_times([[f"{DAYS[29]}T21:05:00.000Z", DAYS[29], "2.02"]])
        row = watch.morning_row("AAA", b, 56.0, EVENT_BARS[:2], acc, DAYS[29], DAYS[30])
        self.assertTrue(row["earnings"])
        self.assertTrue(row["status"].startswith("PASSES so far"))
        self.assertEqual(row["orh"], 57.0)
        low = [x[:5] + [1e5] for x in EVENT_BARS[:2]]
        self.assertIn("fails volume", watch.morning_row("AAA", b, 56.0, low, acc, DAYS[29], DAYS[30])["status"])
        self.assertIn("no earnings", watch.morning_row("AAA", b, 56.0, EVENT_BARS[:2], [], DAYS[29], DAYS[30])["status"])
        tight = series([50.0] * 30, highs=[50.5] * 30, lows=[49.5] * 30)    # 2% normal range < 3.6% stop
        self.assertIn("fails range", watch.morning_row("AAA", tight, 56.0, EVENT_BARS[:2], acc, DAYS[29], DAYS[30])["status"])

    def test_event_log_excess_returns(self):
        api = FakeApi()
        daily = {"AAA": api.daily["AAA"]}
        intraday = {("AAA", EVENT): EVENT_BARS}
        spy_intraday = {EVENT: api.intraday[("SPY", EVENT)]}
        rows = watch.event_log({EVENT: ["AAA"]}, daily, intraday, {}, api.daily["SPY"], spy_intraday)
        k = DAYS.index(EVENT)
        ref = 56.6                                                            # close of the last bar before 10:30
        expect5 = round(100 * (api.daily["AAA"]["close"][k + 5] / ref - 1) - 100 * (api.daily["SPY"]["close"][k + 5] / 400.0 - 1), 2)
        self.assertEqual(rows[0]["d5"], expect5)
        self.assertNotIn("d20", rows[0])                                      # not enough days yet
        self.assertFalse(rows[0]["earnings"])

    def test_summarize(self):
        s = watch.summarize([1.0, 2.0, 3.0])
        self.assertEqual((s["n"], s["mean"], s["median"], s["pct_positive"]), (3, 2.0, 2.0, 100))
        self.assertAlmostEqual(s["t"], 3.46, places=2)
        self.assertEqual(watch.summarize([]), {"n": 0})

    def test_phases(self):
        self.assertEqual(watch.phase("2026-10-05"), "before")
        self.assertEqual(watch.phase("2026-10-06"), "events")
        self.assertEqual(watch.phase("2027-01-08"), "events")
        self.assertEqual(watch.phase("2027-01-11"), "tracking")
        self.assertEqual(watch.phase("2027-02-13"), "finished")


class EndToEndTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(watch, "OUT", Path(self.tmp.name)),
                        mock.patch.object(watch, "universe", lambda: ["AAA", "BBB"]),
                        mock.patch.object(watch, "START_DAY", DAYS[60]),
                        mock.patch.object(watch, "LAST_EVENT_DAY", DAYS[75]),
                        mock.patch.object(watch, "STOP_DAY", DAYS[79]),
                        mock.patch.object(watch, "HISTORY_DAYS", 120)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_morning_list(self):
        rows = watch.morning(FakeApi(), FakeSec(), EVENT)
        self.assertEqual([r["symbol"] for r in rows], ["AAA"])
        self.assertTrue(rows[0]["status"].startswith("PASSES so far"))
        self.assertIn("AAA gap +12.0%", watch.morning_text(EVENT, rows))

    def test_evening_matches_the_backtest_code(self):
        api, sec = FakeApi(), FakeSec()
        snap = watch.evening(api, sec, TODAY)
        main = snap["ledgers"]["main"]["trades"]
        self.assertEqual([(t["symbol"], t["entry_date"]) for t in main], [("AAA", EVENT)])
        info = snap["ledgers"]["all_catalysts"]["trades"]
        self.assertEqual(sorted(t["symbol"] for t in info), ["AAA", "BBB"])
        # the same answer straight from the test #16 functions
        daily = {s: dict(api.daily[s]) for s in ("AAA", "BBB")}
        for b in daily.values():
            b["_idx"] = {d: n for n, d in enumerate(b["date"])}
        accepted = {"AAA": bt.acceptance_times(sec.rows("AAA")), "BBB": []}
        events, _, _ = bt.build_events({EVENT: ["AAA"], OTHER: ["BBB"]}, daily,
                                       {("AAA", EVENT): EVENT_BARS, ("BBB", OTHER): EVENT_BARS}, accepted)
        trades, curve, _ = bt.portfolio(events, daily, [d for d in DAYS if DAYS[60] <= d <= TODAY])
        self.assertEqual(main, trades)
        self.assertAlmostEqual(snap["ledgers"]["main"]["curve"][-1][1], curve[-1][1])
        self.assertTrue(main[0]["open"])                                      # half sold on day 3, rest still riding
        text = watch.evening_text(snap)
        self.assertIn("Main rule (earnings EP)", text)
        self.assertIn("open: AAA", text)


if __name__ == "__main__":
    unittest.main()
