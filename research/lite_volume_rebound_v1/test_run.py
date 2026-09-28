import unittest
from types import SimpleNamespace

from research.lite_volume_rebound_v1.run import decision, simulate


def bar(o=98, h=None, l=None, c=None, v=100):
    c = o if c is None else c
    h = max(o, c) if h is None else h
    l = min(o, c) if l is None else l
    return SimpleNamespace(o=o, h=h, l=l, c=c, v=v)


def session(volume=100, qualify=True, fill=True, later_target=False, last_close=98):
    bars = [bar(v=volume) for _ in range(78)]
    bars[0] = bar(o=100, h=100, l=98, c=98, v=volume)
    for index, close in zip((3, 4, 5), (97, 97.5, last_close)):
        bars[index] = bar(o=close, v=volume)
    if not qualify:
        bars[4] = bar(o=97, v=volume)
    bars[6] = bar(o=99, h=105, l=97 if fill else 98.5,
                  c=98 if fill else 98.5, v=volume)
    if later_target:
        bars[7] = bar(o=99, h=100, l=98, c=99, v=volume)
    return bars


def history(candidate=None):
    days = {f"2026-01-{number:02}": session() for number in range(1, 21)}
    days["2026-01-21"] = candidate or session(volume=200)
    return days


class VolumeReboundTests(unittest.TestCase):
    def test_volume_uses_only_preceding_twenty_first_half_hours(self):
        days = history()
        result = simulate(days)
        self.assertEqual(result["qualified_days"], 1)
        self.assertEqual(result["decisions"][0]["prior_20_mean_volume"], "600")
        self.assertEqual(result["decisions"][0]["morning_volume"], "1200")
        # Later bars and a later session cannot affect the 10:00 decision.
        days["2026-01-21"][7].v = 10**9
        days["2026-01-22"] = session(volume=10**9)
        self.assertEqual(simulate(days)["decisions"][0], result["decisions"][0])
        self.assertIsNone(decision(days["2026-01-21"], [days[key] for key in sorted(days)[:19]]))

    def test_recent_flat_ledger_keeps_prior_history_for_warmup(self):
        days = history()
        result = simulate(days, {"2026-01-21"})
        self.assertEqual(result["session_count"], 1)
        self.assertEqual(result["qualified_days"], 1)
        self.assertEqual(result["entries"], 1)

    def test_entry_bar_high_does_not_close_and_unresolved_loss_is_marked(self):
        days = history()
        result = simulate(days)
        self.assertEqual(result["entries"], 1)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(result["unresolved_positions"], 1)
        self.assertLess(float(result["unresolved"]["marked_pnl"]), 0)

    def test_later_target_and_occupied_candidate(self):
        days = history(session(volume=200, later_target=True))
        days["2026-01-22"] = session(volume=300)
        result = simulate(days)
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["unresolved_positions"], 1)
        self.assertEqual(result["trades"][0]["exit_bar_index"], 7)
        self.assertGreater(float(result["trades"][0]["pnl"]), 0)
        days["2026-01-21"] = session(volume=200)
        days["2026-01-22"] = [bar(o=88, v=300) for _ in range(78)]
        days["2026-01-22"][0] = bar(o=90, l=88, c=88, v=300)
        for index, close in zip((3, 4, 5), (87, 87.5, 88)):
            days["2026-01-22"][index] = bar(o=close, v=300)
        occupied = simulate(days)
        self.assertEqual(occupied["skipped_occupied"], 1)
        self.assertEqual(occupied["closed_trades"], 0)
        self.assertEqual(occupied["unresolved_positions"], 1)
        self.assertLess(float(occupied["unresolved"]["marked_pnl"]), 0)

    def test_limit_expiry_and_net_profit_cost_gate(self):
        days = history(session(volume=200, fill=False))
        result = simulate(days)
        self.assertEqual((result["unfilled_limit"], result["entries"]), (1, 0))
        days["2026-01-21"] = session(volume=200, last_close=99.9)
        days["2026-01-21"][6] = bar(o=99.9, h=105, l=99.8, c=99.9, v=200)
        result = simulate(days, cost_bps=50)
        self.assertEqual(result["skipped_not_net_profitable"], 1)
        self.assertEqual(result["entries"], 0)

    def test_cost_sensitivity_and_cash_only(self):
        days = history(session(volume=200, later_target=True))
        cheap = simulate(days, cost_bps=0)
        costly = simulate(days, cost_bps=25)
        self.assertGreater(float(cheap["net_marked_pnl"]), float(costly["net_marked_pnl"]))
        poor = simulate(days, cost_bps=10)
        self.assertGreaterEqual(float(poor["daily"][-1]["cash"]), 0)


if __name__ == "__main__":
    unittest.main()
