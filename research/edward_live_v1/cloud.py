"""EdwardAlerts cloud relay: your $300 order details and an instant paper copy for every Edward alert, Mac off.

Flow: Edward posts -> Discord push on your iPhone -> a Shortcut automation (Notification trigger, title contains
"EdwardAlerts") does two things:
  1. a Pushover Critical Alert straight from the phone (rings through Do Not Disturb; never depends on this server);
  2. POSTs the notification to a private ntfy.sh inbox topic.
This service (always on, personal DigitalOcean server; a streaming subscription, so no open ports) reads the inbox.
For an entry it first rings the phone (Pushover priority 1, through Do Not Disturb) with the $300 order and a button
that opens the stock in the Robinhood app, before any broker call. It then places the paper copy in ...U036
(research/edward_live_v1/copier.py) and files the result silently in the Pushover app, so the alert stays on top.
On iOS a plain tap opens Pushover; press and hold the alert for its "Open URL" button. Robinhood's app links cover
only /stocks/<ticker>, so expiry, strike and the limit order stay manual taps. His full exits ("stopped out",
"sell all") close the paper copy (one quiet note). A 4:05 PM ET weekday note sums up the day and doubles as a heartbeat.

Inbox message (the Shortcut's Text action, one item per line):
    EDW1 <inbox key>
    <notification title>
    <notification subtitle, may be empty>
    <notification body ...>
Anything without the right key is ignored. Paper only: it never touches Discord or a real-money account.

  PYTHONPATH=src:. .venv/bin/python -m research.edward_live_v1.cloud make-inbox   # once: inbox + private Shortcut card
  ... cloud send-test '$QQQ 720 PUT 10/24 @ 0.73'   # post a fake alert into the inbox (end-to-end test)
  ... cloud run                                      # the service (systemd unit edward-relay on the server)
  ... cloud status                                   # on the server: heartbeat, recent posts, paper copies
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import json
import os
import queue
import re
import secrets
import threading
import time as clock
import urllib.request

from research.edward_live_v1 import notify
from research.edward_live_v1.copier import Alpaca, Copier, et
from research.edward_live_v1.parse import parse, push_text, ticket
from research.edward_live_v1.relay import LATE_MIN, OUT, load, save, write_env

EVENTS, STATE, CARD = OUT / "cloud_events.jsonl", OUT / "cloud_state.json", OUT / "SHORTCUT_CARD.md"
NTFY = "https://ntfy.sh"
AUTHOR = re.compile(r"^\s*(?:Edward Johnson|EdwardAlerts(?: A\+)?|Edward)\s*:\s*", re.I)
SUMMARY_AT, STALE_S = time(16, 5), 600


def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):,.0f}"


def read_inbox(text, key):
    """Inbox text -> (title, subtitle, body), or None unless the first line is 'EDW1 <key>'."""
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not secrets.compare_digest(lines[0].strip().encode(), f"EDW1 {key}".encode()):
        return None
    lines += ["", ""]
    return lines[1].strip(), lines[2].strip(), "\n".join(lines[3:]).strip()


def label_of(title, subtitle):
    t = f"{title} {subtitle}".lower()
    return "free" if ("a+" in t or "trade-ideas" in t) else "vip" if "alerts" in t else "edward"


def handle_inbox(msg, copier, now, push=notify.push):
    """One key-checked inbox message -> phone pushes + paper action. Returns the log record.

    Entries ring first (your order + a Robinhood button), then the paper copy; exits get one quiet note."""
    posted = datetime.fromtimestamp(msg["time"], timezone.utc)
    label = label_of(msg["title"], msg["subtitle"])
    text = AUTHOR.sub("", msg["body"]) or AUTHOR.sub("", msg["subtitle"])
    ev = parse(text, et(posted).date())
    rec = {"at": now.isoformat(), "posted": posted.isoformat(), "channel": label, "msg_id": msg["id"],
           "author": msg["title"], **ev}
    sym = ev.get("underlying")
    link = {"url": f"https://robinhood.com/stocks/{sym}", "url_title": f"Open {sym} in Robinhood"} if sym else {}
    title, message, _ = push_text(ev, label)
    title = ("TEST " if msg["title"].startswith("TEST") else "") + "📋 " + title.split(" ", 1)[1]
    if ev["kind"] == "entry":
        late = (now - posted).total_seconds() > LATE_MIN * 60
        loud = not late and ticket(ev["price"])["contracts_at_his_price"] > 0  # nothing to buy or too old: no ring
        rec["pushed"] = push(("(late) " if late else "") + title, message, priority=1 if loud else -1, **link)
    result = None
    try:
        if copier is not None and ev["kind"] == "entry":
            result = copier.entry(ev, f"n-{msg['id']}", label, posted, now)
        elif copier is not None and ev["kind"] == "exit":
            result = copier.exit(ev, label, now)
    except Exception as exc:  # a broker hiccup must not stop the log
        result = {"summary": f"Paper copy error: {type(exc).__name__}: {str(exc)[:160]}"}
    if result:
        rec["copy"] = result["summary"]
        if ev["kind"] == "entry":  # priority -2: in the Pushover app only, no banner over the alert above
            rec["copy_pushed"] = push("📝 Paper copy", result["summary"], priority=-2, **link)
        else:
            rec["pushed"] = push(title, result["summary"], priority=-1, **link)
    OUT.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


class Inbox(threading.Thread):
    """Streams the ntfy topic. After any drop it reconnects with `since=<last id>`, so ntfy's 12-hour cache fills
    the gap. ntfy sends a keepalive every ~45 s, so `seen_at` going stale means the connection is down."""

    def __init__(self, topic, since, out, server=NTFY, opener=urllib.request.urlopen):
        super().__init__(daemon=True)
        self.url, self.since, self.out, self.opener = f"{server}/{topic}/json", since, out, opener
        self.seen_at, self.error = clock.monotonic(), None

    def pump_once(self):
        with self.opener(f"{self.url}?since={self.since}", timeout=90) as r:
            for line in r:
                ev = json.loads(line)
                self.seen_at, self.error = clock.monotonic(), None
                if ev.get("event") == "message":
                    self.since = ev["id"]
                    self.out.put(ev)

    def run(self):
        wait = 1
        while True:
            try:
                self.pump_once()
                wait = 1
            except Exception as exc:
                self.error = f"{type(exc).__name__}: {str(exc)[:120]}"
            clock.sleep(wait)
            wait = min(wait * 2, 60)


def daily_summary(st, now, copier, push=notify.push):
    """Weekdays at 4:05 PM ET: today's paper copies and this week's P&L (quiet)."""
    t = et(now)
    if t.weekday() >= 5 or t.time() < SUMMARY_AT or st.get("summary") == t.date().isoformat():
        return False
    st["summary"] = t.date().isoformat()
    copies = list(copier.st["copies"].values())
    today = [c for c in copies if et(datetime.fromisoformat(c["alert_ts"])).date() == t.date()]
    closed = [c for c in copies if c.get("closed_at") and et(datetime.fromisoformat(c["closed_at"])).date() == t.date()]
    held = [c for c in copies if c["status"] in ("open", "exiting")]
    held_pnl = sum((c["mark"] - c["fill"]) * c["qty_open"] * 100 for c in held if c.get("mark") is not None)
    push("Edward paper copies: today",
         f"Alerts copied: {sum(c.get('fill') is not None for c in today)} of {len(today)}\n"
         f"Closed today: {money(sum(c.get('pnl') or 0 for c in closed))}\n"
         f"Still open: {len(held)} ({money(held_pnl)})\n"
         f"This week: {money(copier.week_pnl(now))} (stop at -$1,500)", priority=-1)
    return True


def run(args):
    cfg = notify.config()
    topic, key = cfg.get("EDWARD_INBOX_TOPIC"), cfg.get("EDWARD_INBOX_KEY")
    if not (topic and key):
        raise SystemExit("No inbox yet: run `cloud make-inbox`, then redeploy.")
    st = load(STATE, {})
    copier, q = Copier(Alpaca()), queue.Queue()
    inbox = Inbox(topic, st.get("since") or str(int(clock.time())), q)
    inbox.start()
    print(f"Edward cloud relay running: inbox -> order details + paper copy (...U036); "
          f"phone channels: {notify.channels(cfg) or 'none yet'}", flush=True)
    beat, warned = 0.0, False
    while True:
        try:
            ev = q.get(timeout=1)
        except queue.Empty:
            ev = None
        now = datetime.now(timezone.utc)
        if ev:
            st["since"] = ev["id"]
            seen = st.setdefault("seen", [])
            if ev["id"] not in seen:
                st["seen"] = (seen + [ev["id"]])[-500:]
                msg = read_inbox(ev.get("message"), key)
                if msg is None:
                    print(f"{et(now):%H:%M:%S} ignored an inbox message without the key", flush=True)
                else:
                    rec = handle_inbox({"id": ev["id"], "time": ev["time"], "title": msg[0], "subtitle": msg[1],
                                        "body": msg[2]}, copier, now)
                    print(f"{et(now):%H:%M:%S} {rec['channel']} {rec['kind']}: {rec['text'][:80]!r} "
                          f"push={rec.get('pushed')} {rec.get('copy', '')}", flush=True)
        try:
            copier.tick(now)
        except Exception as exc:
            print(f"{et(now):%H:%M:%S} copier check failed: {type(exc).__name__}: {exc}", flush=True)
        if daily_summary(st, now, copier):
            save(STATE, st)  # never send the same day's summary twice after a restart
        stale = clock.monotonic() - inbox.seen_at > STALE_S
        if stale != warned:
            warned = stale
            if stale:
                notify.push("⚠️ Edward cloud relay lost its inbox",
                            f"No connection to ntfy for 10+ minutes ({inbox.error}). Your phone's own alert still "
                            "works; order details and paper copies are paused.", priority=1)
            else:
                notify.push("Edward cloud relay reconnected", "Order details and paper copies are back.", priority=-1)
        if ev or clock.monotonic() - beat > 30:
            st["heartbeat"], beat = now.isoformat(), clock.monotonic()
            save(STATE, st)


def make_inbox(args):
    cfg = notify.config()
    topic = cfg.get("EDWARD_INBOX_TOPIC") or "edw-" + secrets.token_hex(12)
    key = cfg.get("EDWARD_INBOX_KEY") or secrets.token_hex(8)
    write_env({"EDWARD_INBOX_TOPIC": topic, "EDWARD_INBOX_KEY": key})
    OUT.mkdir(parents=True, exist_ok=True)
    fd = os.open(CARD, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"""# Edward Shortcut card (private: don't share)

Add these two actions to your Edward automation, **after** the Pushover action.

**Action 2: Text** (four lines; tap each [ ] to insert the Notification variable's field)

    EDW1 {key}
    [Notification → Title]
    [Notification → Subtitle]
    [Notification → Body]

**Action 3: Get Contents of URL**
- URL: `{NTFY}`
- Method: **POST**
- Request Body: **JSON**, two Text fields:
  - `topic` = `{topic}`
  - `message` = [Text]  (the output of action 2)

Then your cloud server answers each entry with a loud "📋" Pushover alert: your order and an "Open in Robinhood"
button (press and hold the alert). The paper fill lands silently in the Pushover app.
""")
    print(f"Inbox ready (topic and key saved in .env.edward). Private Shortcut card: {CARD}")


def send_test(args):
    cfg = notify.config()
    body = f"EDW1 {cfg['EDWARD_INBOX_KEY']}\nTEST Edward Johnson (#🚨|alerts, EdwardAlerts)\n\n{args.text}"
    req = urllib.request.Request(NTFY, method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"topic": cfg["EDWARD_INBOX_TOPIC"], "message": body}).encode())
    with urllib.request.urlopen(req, timeout=10) as r:
        print("posted to the inbox:", r.status, json.load(r)["id"])


def status(args):
    st = load(STATE, {})
    beat = st.get("heartbeat")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds() if beat else None
    print(f"cloud relay heartbeat: {'never' if age is None else f'{age:.0f} s ago'}"
          f"{'  (NOT RUNNING?)' if age is None or age > 120 else ''}; "
          f"phone channels: {notify.channels(notify.config()) or 'none'}")
    if EVENTS.exists():
        print("\nlast posts:")
        for line in EVENTS.read_text().splitlines()[-10:]:
            r = json.loads(line)
            print(f"  {et(datetime.fromisoformat(r['posted'])):%m/%d %H:%M} {r['channel']:6} {r['kind']:6} "
                  f"{r['text'][:60]!r} {r.get('copy', '')}")
    print("\npaper copies:", json.dumps(Copier(None).report(datetime.now(timezone.utc)), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("make-inbox")
    t = sub.add_parser("send-test")
    t.add_argument("text")
    sub.add_parser("status")
    a = ap.parse_args()
    {"run": run, "make-inbox": make_inbox, "send-test": send_test, "status": status}[a.cmd](a)


if __name__ == "__main__":
    main()
