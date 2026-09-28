from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cloud.stock_runtime_supervisor import run_once, assess_day, session_bounds, session_report
from cloud.free_stock_provider_v3 import build_cycle, ProviderBlocked
from cloud.test_free_stock_provider import FakeClient, NOW
from research.agentic_stock_paper_free_v2.test_runtime import cycle


class CurrentClient(FakeClient):
    def get(self, host, path, query, *, alpaca):
        body, raw = super().get(host,path,query,alpaca=alpaca)
        if path.endswith("snapshots"):
            for value in body["snapshots"].values():
                value["dailyBar"]["t"] = NOW.isoformat()
            raw = self.raw(body)
        return body,raw


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.input = self.root / "input.json"
        self.status = self.root / "provider.json"
        self.raw = cycle()
        self.input.write_text(json.dumps(self.raw))
        self.provider = {"status":"PROVIDER_CYCLE_READY", "cycle_id":self.raw["cycle_id"], "checked_at":NOW.isoformat()}
        self.status.write_text(json.dumps(self.provider))

    def tearDown(self): self.tmp.cleanup()
    def run_cycle(self, now=NOW): return run_once(self.input,self.status,self.state,now)

    def test_fresh_fill_replay_and_stale_replay(self):
        first = self.run_cycle()
        self.assertEqual(first["status"], "PAPER_STOCK_CYCLE_COMPLETE")
        self.assertTrue(any("fill" in e for e in first["events"]))
        self.assertEqual(self.run_cycle()["status"], "NO_NEW_CYCLE")
        before = (self.state/"stock.sqlite").read_bytes()
        stale = self.run_cycle(NOW + timedelta(minutes=6))
        self.assertEqual(stale["status"], "BLOCKED_DATA")
        self.assertEqual(before,(self.state/"stock.sqlite").read_bytes())

    def test_blocked_provider_cannot_reuse_ready_file(self):
        self.status.write_text(json.dumps({"status":"BLOCKED_DATA", "reason":"stale quote"}))
        result = self.run_cycle()
        self.assertIn("provider blocked",result["reason"])
        self.assertFalse(self.state.exists())

    def test_future_and_mismatched_provider_rejected(self):
        for change in ({"checked_at":(NOW+timedelta(seconds=1)).isoformat()}, {"cycle_id":"wrong"}):
            self.status.write_text(json.dumps({**self.provider,**change}))
            self.assertEqual(self.run_cycle()["status"],"BLOCKED_DATA")
            self.assertFalse(self.state.exists())

    def test_closed_and_weekend_never_fill(self):
        for now in (datetime(2026,9,16,20,5,tzinfo=timezone.utc),datetime(2026,9,19,17,tzinfo=timezone.utc)):
            self.assertEqual(self.run_cycle(now)["status"],"MARKET_CLOSED")
        self.assertFalse(self.state.exists())

    def test_completed_session_independent_of_fresh_quotes(self):
        self.state.mkdir()
        start,end = session_bounds("2026-09-17")
        with sqlite3.connect(self.state/"runtime.sqlite") as db:
            db.execute("CREATE TABLE cycles(created_at TEXT,output_json TEXT,status TEXT)")
            for i in range(78):
                point=(start+timedelta(minutes=5*i)).astimezone(timezone.utc).isoformat()
                out={"decision_at":point,"status":"PAPER_STOCK_CYCLE_COMPLETE"}
                db.execute("INSERT INTO cycles VALUES(?,?,?)",(point,json.dumps(out),"COMPLETE"))
        self.assertEqual(session_report(self.state,end)["completed_sessions"],0)
        result = self.run_cycle(end+timedelta(minutes=5))
        self.assertEqual(result["status"],"MARKET_CLOSED")
        self.assertEqual(result["session_coverage"]["qualified_sessions"],1)
        self.assertEqual(self.run_cycle(end+timedelta(minutes=10))["session_coverage"]["qualified_sessions"],1)

    def test_partial_and_gap_sessions_do_not_qualify(self):
        start,end = session_bounds("2026-09-17")
        full=[start+timedelta(minutes=5*i) for i in range(78)]
        self.assertEqual(assess_day("2026-09-17",full)["status"],"QUALIFIED")
        for points in ([],full[30:],full[:30]+full[40:],full[:-10]):
            self.assertEqual(assess_day("2026-09-17",points)["status"],"INCOMPLETE_COVERAGE")

    def test_pending_crash_latches_before_processing(self):
        self.run_cycle()
        with sqlite3.connect(self.state/"runtime.sqlite") as db:
            db.execute("UPDATE cycles SET status='PENDING'")
        self.assertIn("pending cycle",self.run_cycle()["reason"])

    def test_provider_current_bar_and_closed_market(self):
        self.assertEqual(len(build_cycle(CurrentClient(),NOW)["stock_entries"]),5)
        with self.assertRaisesRegex(ProviderBlocked,"outside regular"):
            build_cycle(CurrentClient(),NOW.replace(hour=21))
        class OldBar(CurrentClient):
            def get(self,*args,**kwargs):
                value,raw=super().get(*args,**kwargs)
                for row in value.get("snapshots",{}).values(): row["dailyBar"]["t"]=(NOW-timedelta(days=1)).isoformat()
                return value,raw
        with self.assertRaisesRegex(ProviderBlocked,"different day"):
            build_cycle(OldBar(),NOW)

    def test_v3_crossed_quote_rejected(self):
        class Crossed(CurrentClient):
            def get(self,*args,**kwargs):
                value,raw=super().get(*args,**kwargs)
                for row in value.get("snapshots",{}).values():
                    row["latestQuote"]["ap"]=90
                return value,self.raw(value)
        with self.assertRaisesRegex(ProviderBlocked,"crossed"):
            build_cycle(Crossed(),NOW)

    def test_v3_truncated_history_rejected(self):
        class Truncated(CurrentClient):
            def get(self,*args,**kwargs):
                value,raw=super().get(*args,**kwargs)
                if "bars" in value: value["next_page_token"]="more-history"
                return value,self.raw(value)
        with self.assertRaisesRegex(ProviderBlocked,"pagination"):
            build_cycle(Truncated(),NOW)

    def test_v3_stale_quote_rejected(self):
        with self.assertRaisesRegex(ProviderBlocked,"stale"):
            build_cycle(CurrentClient(stale=True),NOW)

    def test_v3_malformed_calendar_rejected(self):
        with self.assertRaisesRegex(ProviderBlocked,"earnings calendar"):
            build_cycle(CurrentClient(malformed_calendar=True),NOW)

    def test_v3_empty_weekend_calendar_valid(self):
        self.assertEqual(len(build_cycle(CurrentClient(weekend_none=True),NOW)["stock_entries"]),5)


if __name__ == "__main__": unittest.main()
