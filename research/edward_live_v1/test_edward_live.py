from datetime import date, datetime, timezone
import json
import plistlib
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from research.edward_live_v1 import copier as cp, notify, relay
from research.edward_live_v1.parse import parse, posted_at, push_text, ticket, tick

DAY = date(2026, 10, 19)
NOW = datetime(2026, 10, 19, 16, 24, tzinfo=timezone.utc)  # 12:24 PM ET, Monday
VIP_G, VIP_C = "1180233578467053659", "1324790086885314670"


def snowflake(dt):
    return str((int(dt.timestamp() * 1000) - 1420070400000) << 22)


def note_blob(body, guild=VIP_G, channel=VIP_C, msg=None, title="Edward Johnson (#🚨|alerts, EdwardAlerts)"):
    msg = msg or snowflake(datetime(2026, 10, 19, 16, 23, tzinfo=timezone.utc))
    usda = plistlib.dumps({"$version": 100000, "$archiver": "NSKeyedArchiver", "$top": {"root": plistlib.UID(1)},
                           "$objects": ["$null", "fallbackDeepLink",
                                        f"discord://discord.com/channels/{guild}/{channel}/{msg}"]},
                          fmt=plistlib.FMT_BINARY)
    req = {"titl": "⁨" + title.replace(" (", "⁩ (", 1), "body": body, "thre": channel, "iden": msg, "usda": usda}
    return plistlib.dumps({"app": "com.hnc.Discord", "date": 814153833.8, "req": req}, fmt=plistlib.FMT_BINARY)


class ParseTest(unittest.TestCase):
    def test_entries(self):
        e = parse("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO @everyone", DAY)
        self.assertEqual((e["kind"], e["symbol"], e["price"], e["zero_dte"]), ("entry", "QQQ261019P00720000", 0.73, True))
        self.assertEqual(e["tags"], ["0DTE", "LOTTO"])
        e = parse("$TSLA 375 CALL 10/16 @ 1.00\n\nLOTTO @everyone", date(2026, 10, 16))
        self.assertEqual((e["symbol"], e["tags"]), ("TSLA261016C00375000", ["LOTTO"]))
        e = parse("$HOOD 113 CALL 10/16 @ 1.27  SIZED IN FOR 0 @everyone", date(2026, 10, 13))
        self.assertEqual((e["symbol"], e["price"], e["tags"]), ("HOOD261016C00113000", 1.27, ["SIZED FOR 0"]))
        self.assertEqual(parse("$SPY 777C 10/7 @ 1.20", date(2026, 10, 6))["symbol"], "SPY261007C00777000")
        self.assertEqual(parse("$PLTR 207.5C 10/16 @2.71", date(2026, 10, 9))["symbol"], "PLTR261016C00207500")
        self.assertEqual(parse("$NVDA 150 CALL 1/16 @ 2.10 SWING", date(2026, 12, 20))["expiry"], "2027-01-16")

    def test_updates_trims_exits_notes(self):
        cases = {"$QQQ +25% here @everyone": ("update", "QQQ", 25.0, None),
                 "$QQQ @ 1.08 | 47% trimming @everyone": ("trim", "QQQ", 47.0, 1.08),
                 "$QQQ UP 94% AT 1.42 ☢️ @everyone": ("update", "QQQ", 94.0, 1.42),
                 "$TSLA @ 1.60 | 60% @everyone": ("update", "TSLA", 60.0, 1.60),
                 "SCSC out majority": ("trim", None, None, None),
                 "SOLD MAJORITY": ("trim", None, None, None),
                 "trim most": ("trim", None, None, None),
                 "$NVDA stopped out": ("exit", "NVDA", None, None),
                 "Gap filled you can sell all": ("exit", None, None, None),
                 "dont let it go red ❤️": ("note", None, None, None),
                 "Do you guys want more $QQQ / $SPY trades?": ("note", "QQQ", None, None),
                 "No good trades that im seeing currently guys. Money is rotating in/out of sectors.": ("note", None, None, None),
                 "Most traders lose money": ("note", None, None, None)}
        for text, want in cases.items():
            ev = parse(text, DAY)
            self.assertEqual((ev["kind"], ev["underlying"], ev["pct"], ev["price"]), want, text)

    def test_ticket_follows_the_owners_table(self):
        self.assertEqual(tick(0.876), 0.87)
        self.assertEqual(tick(3.252), 3.25)
        self.assertEqual(tick(1.17, up=True), 1.17)
        t = ticket(0.73)
        self.assertEqual((t["max_price"], t["contracts_at_his_price"], t["contracts_at_max"]), (0.87, 4, 3))
        self.assertIn("Buy 4 if you can get ≤ $0.75, else 3 up to $0.87", t["line"])
        self.assertIn("Buy 3 if you can get ≤ $1.00, else 2 up to $1.20", ticket(1.00)["line"])
        self.assertIn("Buy 1 at up to $2.40 (max $240)", ticket(2.00)["line"])
        self.assertIn("Buy 1 if you can get ≤ $3.00, skip above that", ticket(2.71)["line"])
        self.assertTrue(ticket(3.50)["line"].startswith("Skip"))

    def test_push_text(self):
        title, msg, pri = push_text(parse("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO @everyone", DAY), "vip")
        self.assertEqual((title, pri), ("🚨 VIP: QQQ 720 PUT 10/19 @ 0.73", 2))
        self.assertIn("0DTE · LOTTO", msg)
        title, _, pri = push_text(parse("$QQQ UP 94% AT 1.42", DAY), "vip")
        self.assertEqual((title, pri), ("📈 VIP UPDATE: QQQ +94% at 1.42", 1))
        self.assertEqual(push_text(parse("dont let it go red", DAY), "free", "EdwardAlerts")[2], 0)

    def test_snowflake_time(self):
        when = datetime(2026, 10, 19, 16, 23, 5, tzinfo=timezone.utc)
        self.assertEqual(posted_at(snowflake(when)), when)


class RelayTest(unittest.TestCase):
    def make_db(self, path, bodies):
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE app (app_id INTEGER PRIMARY KEY, identifier VARCHAR, badge INTEGER NULL)")
        con.execute("CREATE TABLE record (rec_id INTEGER PRIMARY KEY, app_id INTEGER, uuid BLOB, data BLOB, "
                    "request_date REAL, request_last_date REAL, delivered_date REAL, presented Bool, style INTEGER, "
                    "snooze_fire_date REAL)")
        con.executemany("INSERT INTO app VALUES (?, ?, NULL)", [(1, "com.hnc.discord"), (2, "com.apple.mobilesms")])
        for i, (app, blob) in enumerate(bodies, start=10):
            con.execute("INSERT INTO record (rec_id, app_id, data) VALUES (?, ?, ?)", (i, app, blob))
        con.commit()
        con.close()

    def test_only_edwards_two_channels_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db"
            other = note_blob("Halloween drop!", guild="1540259007447572601", channel="1540261259314855976",
                              title="Perry (#announcements, ANNOUNCEMENTS)")
            free = note_blob("$TSLA 375 CALL 10/16 @ 1.00 LOTTO", guild="1549505693529411614",
                             channel="1549505694863069297", msg="1428000000000000000",
                             title="EdwardAlerts (#🚨|trade-ideas, EdwardAlerts A+)")
            self.make_db(db, [(1, other), (2, b"not discord"), (1, note_blob("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO")),
                              (1, free)])
            posts, top = relay.read_new(0, db)
            self.assertEqual(top, 13)
            self.assertEqual([(p["label"], p["author"]) for p in posts], [("vip", "Edward Johnson"), ("free", "EdwardAlerts")])
            self.assertTrue(posts[0]["link"].startswith(f"https://discord.com/channels/{VIP_G}/{VIP_C}/"))
            self.assertEqual(relay.read_new(13, db), ([], 13))

    def test_handle_pushes_then_logs(self):
        post = relay.decode(1, note_blob("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO @everyone"))
        sent = []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(relay, "OUT", Path(tmp)), \
                mock.patch.object(relay, "EVENTS", Path(tmp) / "events.jsonl"):
            rec = relay.handle(post, None, NOW, push=lambda *a, **k: sent.append((a, k)) or {"pushover": "ok"})
            logged = json.loads((Path(tmp) / "events.jsonl").read_text())
        self.assertEqual(rec["kind"], "entry")
        self.assertEqual(sent[0][1]["priority"], 2)
        self.assertEqual(logged["symbol"], "QQQ261019P00720000")
        late = relay.decode(1, note_blob("$QQQ UP 94% AT 1.42", msg=snowflake(datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc))))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(relay, "OUT", Path(tmp)), \
                mock.patch.object(relay, "EVENTS", Path(tmp) / "events.jsonl"):
            relay.handle(late, None, NOW, push=lambda *a, **k: sent.append((a, k)) or {})
        self.assertTrue(sent[-1][0][0].startswith("(late)"))
        self.assertEqual(sent[-1][1]["priority"], 0)


class FakeApi:
    def __init__(self, bid=0.70, ask=0.78, fill_buys=True):
        self.q, self.fill_buys, self.orders, self.sent, self.canceled = (bid, ask), fill_buys, {}, [], []

    def quote(self, symbol):
        return self.q

    def submit(self, payload):
        oid = f"o{len(self.sent) + 1}"
        self.sent.append(payload)
        filled = payload["side"] == "buy" and self.fill_buys
        self.orders[oid] = {"id": oid, "status": "filled" if filled else "new", "filled_at": "x",
                            "filled_qty": payload["qty"] if filled else "0",
                            "filled_avg_price": payload["limit_price"] if filled else None}
        return {"id": oid}

    def order(self, oid):
        return self.orders[oid]

    def cancel(self, oid):
        self.canceled.append(oid)
        if self.orders[oid]["status"] == "new":
            self.orders[oid]["status"] = "canceled"


class CopierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.api = FakeApi()
        self.c = cp.Copier(self.api, Path(self.tmp.name) / "state.json", sleep=lambda s: None)
        self.ev = parse("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO", DAY)
        self.alert = datetime(2026, 10, 19, 16, 23, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def test_entry_buys_at_ask_then_places_the_target(self):
        r = self.c.entry(self.ev, "m1", "vip", self.alert, NOW)
        buy, target = self.api.sent
        self.assertEqual((buy["qty"], buy["limit_price"], buy["client_order_id"]), ("3", "0.78", "edw-b-m1"))
        self.assertEqual((target["side"], target["limit_price"], target["time_in_force"]), ("sell", "1.17", "day"))
        self.assertIn("bought 3 QQQ 720P 10/19 at 0.78", r["summary"])
        self.assertIsNone(self.c.entry(self.ev, "m1", "vip", self.alert, NOW))  # same post twice: ignored
        again = self.c.entry(self.ev, "m2", "free", self.alert, NOW)
        self.assertIn("already holding", again["summary"])

    def test_swing_target_is_good_till_canceled(self):
        ev = parse("$TSLA 375 CALL 10/23 @ 1.00", DAY)
        self.api.q = (0.95, 1.00)
        self.c.entry(ev, "m1", "vip", self.alert, NOW)
        self.assertEqual((self.api.sent[0]["qty"], self.api.sent[1]["limit_price"], self.api.sent[1]["time_in_force"]),
                         ("3", "1.50", "gtc"))

    def test_skips(self):
        self.api.q = (0.85, 0.90)
        self.assertIn("above your max 0.87", self.c.entry(self.ev, "a", "vip", self.alert, NOW)["summary"])
        closed = datetime(2026, 10, 19, 21, 0, tzinfo=timezone.utc)
        self.assertIn("market closed", self.c.entry(self.ev, "b", "vip", self.alert, closed)["summary"])
        old = datetime(2026, 10, 19, 16, 0, tzinfo=timezone.utc)
        self.assertIn("min old", self.c.entry(self.ev, "c", "vip", old, NOW)["summary"])
        self.assertEqual(self.api.sent, [])

    def test_week_stop(self):
        self.c.st["copies"]["old"] = {"msg_id": "old", "alert_ts": "2026-10-19T14:00:00+00:00", "status": "closed",
                                      "fill": 1.0, "realized": -1500.0, "symbol": "X", "underlying": "X"}
        self.assertIn("past your -$1,500 stop", self.c.entry(self.ev, "m1", "vip", self.alert, NOW)["summary"])

    def test_target_fill_closes_with_profit(self):
        self.c.entry(self.ev, "m1", "vip", self.alert, NOW)
        tp = self.c.st["copies"]["m1"]["tp_id"]
        self.api.orders[tp].update(status="filled", filled_qty="3", filled_avg_price="1.17")
        self.c.tick(NOW)
        copy = self.c.st["copies"]["m1"]
        self.assertEqual((copy["status"], copy["pnl"]), ("closed", 117.0))

    def test_his_exit_sells_at_the_bid(self):
        self.c.entry(self.ev, "m1", "vip", self.alert, NOW)
        r = self.c.exit(parse("$QQQ stopped out", DAY), "vip", NOW)
        self.assertIn("selling 3 QQQ 720P 10/19 at 0.70", r["summary"])
        self.assertEqual(self.api.canceled, ["o2"])  # the +50% target is pulled before selling
        sell = self.api.sent[-1]
        self.assertEqual((sell["side"], sell["limit_price"], sell["client_order_id"]), ("sell", "0.70", "edw-x-m1-1"))
        self.api.orders["o3"].update(status="filled", filled_qty="3", filled_avg_price="0.70")
        self.c.tick(datetime(2026, 10, 19, 16, 30, tzinfo=timezone.utc))
        self.assertEqual(self.c.st["copies"]["m1"]["pnl"], -24.0)

    def test_expiry_day_close_out(self):
        self.c.entry(self.ev, "m1", "vip", self.alert, NOW)
        self.c.tick(datetime(2026, 10, 19, 19, 46, tzinfo=timezone.utc))  # 3:46 PM ET
        self.assertEqual(self.c.st["copies"]["m1"]["exit_reason"], "expiry-day close-out at 3:45 PM")

    def test_paper_guard(self):
        api = cp.Alpaca.__new__(cp.Alpaca)
        api.checked, api.call = False, lambda *a, **k: {"account_number": "PA0000OPE5"}
        with self.assertRaises(SystemExit):
            api.guard()


class CloudTest(unittest.TestCase):
    def setUp(self):
        from research.edward_live_v1 import cloud
        self.cloud = cloud
        self.tmp = tempfile.TemporaryDirectory()
        out = Path(self.tmp.name)
        self.patches = [mock.patch.object(cloud, "OUT", out), mock.patch.object(cloud, "EVENTS", out / "ev.jsonl")]
        for p in self.patches:
            p.start()
        self.api = FakeApi()
        self.copier = cp.Copier(self.api, out / "state.json", sleep=lambda s: None)
        self.sent = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def push(self, title, message, **kw):
        self.sent.append((title, message, kw))
        return {"pushover": "ok"}

    def msg(self, body, title="Edward Johnson (#🚨|alerts, EdwardAlerts)", subtitle="", t=NOW):
        return {"id": "nX1", "time": int(t.timestamp()) - 20, "title": title, "subtitle": subtitle, "body": body}

    def test_read_inbox(self):
        text = "EDW1 k1\nEdward Johnson (#🚨|alerts, EdwardAlerts)\n\n$TSLA 375 CALL 10/16 @ 1.00\n\nLOTTO"
        self.assertEqual(self.cloud.read_inbox(text, "k1"),
                         ("Edward Johnson (#🚨|alerts, EdwardAlerts)", "", "$TSLA 375 CALL 10/16 @ 1.00\n\nLOTTO"))
        self.assertIsNone(self.cloud.read_inbox(text, "other"))
        self.assertIsNone(self.cloud.read_inbox(None, "k1"))
        self.assertEqual(self.cloud.read_inbox("EDW1 k1\r\nT", "k1"), ("T", "", ""))

    def test_labels(self):
        self.assertEqual(self.cloud.label_of("Edward Johnson (#🚨|alerts, EdwardAlerts)", ""), "vip")
        self.assertEqual(self.cloud.label_of("EdwardAlerts A+", "#🚨|trade-ideas"), "free")
        self.assertEqual(self.cloud.label_of("", ""), "edward")

    def test_entry_gets_order_details_and_paper_copy_in_one_quiet_push(self):
        rec = self.cloud.handle_inbox(self.msg("Edward Johnson: $QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO"),
                                      self.copier, NOW, push=self.push)
        (title, message, kw), = self.sent
        self.assertEqual(title, "📋 VIP: QQQ 720 PUT 10/19 @ 0.73")
        self.assertIn("Buy 4 if you can get ≤ $0.75, else 3 up to $0.87.", message)
        self.assertIn("Paper copy: bought 3 QQQ 720P 10/19 at 0.78", message)
        self.assertEqual((kw["priority"], kw["url"]), (-1, "https://robinhood.com/stocks/QQQ"))
        self.assertEqual(self.api.sent[0]["client_order_id"], "edw-b-n-nX1")
        self.assertEqual(json.loads((Path(self.tmp.name) / "ev.jsonl").read_text())["copy"], rec["copy"])

    def test_updates_stay_quiet_and_exits_close_the_copy(self):
        self.cloud.handle_inbox(self.msg("$QQQ 720 PUT 10/19 @ 0.73"), self.copier, NOW, push=self.push)
        self.cloud.handle_inbox(self.msg("$QQQ UP 94% AT 1.42"), self.copier, NOW, push=self.push)
        self.assertEqual(len(self.sent), 1)  # the phone's own alert already showed the update
        self.cloud.handle_inbox(self.msg("$QQQ stopped out"), self.copier, NOW, push=self.push)
        self.assertEqual(self.sent[-1][0], "📋 VIP EXIT: QQQ")
        self.assertIn("selling 3 QQQ 720P 10/19 at 0.70", self.sent[-1][1])

    def test_daily_summary_once_per_weekday(self):
        self.cloud.handle_inbox(self.msg("$QQQ 720 PUT 10/19 @ 0.73"), self.copier, NOW, push=self.push)
        st, at = {}, datetime(2026, 10, 19, 20, 6, tzinfo=timezone.utc)  # 4:06 PM ET
        self.cloud.daily_summary(st, at, self.copier, push=self.push)
        self.cloud.daily_summary(st, at, self.copier, push=self.push)
        summaries = [s for s in self.sent if s[0] == "Edward paper copies: today"]
        self.assertEqual(len(summaries), 1)
        self.assertIn("Alerts copied: 1 of 1", summaries[0][1])
        self.cloud.daily_summary({}, datetime(2026, 10, 24, 20, 6, tzinfo=timezone.utc), self.copier, push=self.push)
        self.assertEqual(len([s for s in self.sent if s[0] == "Edward paper copies: today"]), 1)  # Saturday: none

    def test_inbox_stream_queues_messages_and_resumes_after_the_last_id(self):
        urls = []

        class Stream:
            def __init__(self, lines):
                self.lines = lines

            def __enter__(self):
                return iter(self.lines)

            def __exit__(self, *a):
                return False

        def opener(url, timeout):
            urls.append(url)
            return Stream([b'{"event":"open"}\n', b'{"event":"keepalive"}\n',
                           b'{"event":"message","id":"m9","time":1,"message":"EDW1 k"}\n'])

        q = __import__("queue").Queue()
        inbox = self.cloud.Inbox("edw-t", "1792000000", q, opener=opener)
        inbox.pump_once()
        inbox.pump_once()
        self.assertEqual(urls, ["https://ntfy.sh/edw-t/json?since=1792000000", "https://ntfy.sh/edw-t/json?since=m9"])
        self.assertEqual(q.get_nowait()["id"], "m9")


class NotifyTest(unittest.TestCase):
    def test_pushover_and_ntfy_payloads(self):
        seen = []

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout):
            seen.append(req)
            return Resp()

        cfg = {"PUSHOVER_APP_TOKEN": "t", "PUSHOVER_USER_KEY": "u", "NTFY_TOPIC": "edward-x"}
        out = notify.push("🚨 VIP: QQQ", "msg", priority=2, url="https://discord.com/x", cfg=cfg, opener=opener)
        self.assertEqual(out, {"pushover": "ok", "ntfy": "ok"})
        self.assertIn(b"retry=60", seen[0].data)
        self.assertEqual(json.loads(seen[1].data)["priority"], 5)
        self.assertEqual(notify.push("x", "y", cfg={}, opener=opener), {})


if __name__ == "__main__":
    unittest.main()
