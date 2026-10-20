"""EdwardAlerts relay: only Edward's two Discord channels -> your phone through Do Not Disturb, plus a paper copy.

Reads the Mac's own notification list (the Discord app must be open on this Mac), keeps only VIP #🚨|alerts and free
#🚨|trade-ideas, and for each new post:
  1. pushes it to the phone at once (research/edward_live_v1/notify.py) with the order ticket from the owner's rules;
  2. places the paper copy in the ...U036 Alpaca paper account (research/edward_live_v1/copier.py);
  3. appends it to outputs/edward_live/events.jsonl (gitignored) for /edward scoring.
It never logs in to Discord, never posts there, and never trades real money.

  PYTHONPATH=src:. .venv/bin/python -m research.edward_live_v1.relay run          # the loop; Ctrl-C stops it
  ... relay setup                     # store Pushover keys / make an ntfy topic in .env.edward (hidden input)
  ... relay test-push                 # a sample alert to the phone, to check it rings through Do Not Disturb
  ... relay paste "<post>" --channel vip [--dry-run] [--no-copy]   # handle a pasted post as if it just arrived
  ... relay scan --hours 24           # show Edward posts in the notification list (no push, no orders)
  ... relay status                    # heartbeat, recent posts, paper copies and this week's P&L
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, time, timedelta, timezone
from getpass import getpass
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import sqlite3
import subprocess
import time as clock

from research.edward_live_v1 import notify
from research.edward_live_v1.copier import NY, Alpaca, Copier, et
from research.edward_live_v1.parse import CHANNELS, clean, parse, posted_at, push_text

ROOT = Path(__file__).resolve().parents[2]
DB = Path.home() / "Library/Group Containers/group.com.apple.usernoted/db2/db"
OUT = ROOT / "outputs/edward_live"
EVENTS, STATE = OUT / "events.jsonl", OUT / "relay_state.json"
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
LATE_MIN = 15
CANT_READ = ("Can't open the Mac's notification list from this process (macOS privacy protection). Start the relay "
             "from the Claude app's terminal, or see output/EDWARD_RELAY_SETUP.md.")


# ---- the Mac's notification list ---------------------------------------------------------------------------
def connect(db=DB):
    return closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2))


def max_rec_id(db=DB):
    with connect(db) as con:
        return con.execute("select coalesce(max(rec_id), 0) from record").fetchone()[0]


def read_new(after, db=DB):
    """Discord notifications newer than `after` from Edward's two channels (oldest first) and the new watermark."""
    with connect(db) as con:
        rows = con.execute("select r.rec_id, r.data from record r join app a on a.app_id = r.app_id "
                           "where lower(a.identifier) = 'com.hnc.discord' and r.rec_id > ? order by r.rec_id",
                           (after,)).fetchall()
    return [p for p in (decode(rid, blob) for rid, blob in rows) if p], max([after] + [r[0] for r in rows])


def decode(rec_id, blob):
    """One notification record -> post dict, or None unless it is from one of Edward's two channels."""
    try:
        p = plistlib.loads(blob)
    except Exception:
        return None
    req, link = p.get("req", {}), ""
    try:  # Discord stores the message's deep link (guild/channel/message ids) in the notification's user data
        objs = plistlib.loads(req["usda"]).get("$objects", []) if req.get("usda") else []
        link = next((o for o in objs if isinstance(o, str) and "/channels/" in o), "")
    except Exception:
        pass
    m = re.search(r"/channels/(\d+)/(\d+)/(\d+)", link)
    channel = m[2] if m else str(req.get("thre", ""))
    if channel not in CHANNELS or (m and m[1] != CHANNELS[channel][1]):
        return None
    label, guild = CHANNELS[channel]
    msg_id = m[3] if m else str(req.get("iden", ""))
    title = clean(req.get("titl", ""))
    who = re.fullmatch(r"(.*?) \((#.*?), (.*)\)", title)
    posted = posted_at(msg_id) if msg_id.isdigit() else APPLE_EPOCH + timedelta(seconds=float(p.get("date") or 0))
    return {"rec_id": rec_id, "msg_id": msg_id, "channel": channel, "label": label,
            "author": who[1] if who else title, "text": req.get("body", ""), "posted": posted,
            "link": f"https://discord.com/channels/{guild}/{channel}/{msg_id}"}


# ---- one post ----------------------------------------------------------------------------------------------
def handle(post, copier, now, push=notify.push, dry=False):
    ev = parse(post["text"], et(post["posted"]).date())
    title, message, priority = push_text(ev, post["label"], post["author"])
    late = (now - post["posted"]).total_seconds() > LATE_MIN * 60
    if late:
        title, priority = "(late) " + title, min(priority, 0)
    rec = {"at": now.isoformat(), "posted": post["posted"].isoformat(), "channel": post["label"],
           "msg_id": post["msg_id"], "author": post["author"], **ev}
    if dry:
        print(f"\n[{priority}] {title}\n{message}\n")
        return rec
    rec["pushed"] = push(title, message, priority=priority, url=post["link"], url_title="Open in Discord")
    result = None
    if copier is not None and not late:
        try:
            if ev["kind"] == "entry":
                result = copier.entry(ev, post["msg_id"], post["label"], post["posted"], now)
            elif ev["kind"] == "exit":
                result = copier.exit(ev, post["label"], now)
        except Exception as exc:  # a broker hiccup must not stop the alerts
            result = {"summary": f"Paper copy error: {type(exc).__name__}: {str(exc)[:160]}"}
    if result:
        rec["copy"] = result["summary"]
        push("📝 Paper copy", result["summary"], priority=-1)
    OUT.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


# ---- the loop ----------------------------------------------------------------------------------------------
def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    tmp.replace(path)


def discord_running():
    return subprocess.run(["pgrep", "-x", "Discord"], capture_output=True).returncode == 0


def morning_check(st, now):
    """Once per weekday at 9:25 ET: a quiet 'relay on' note, or a loud warning if Discord isn't open on the Mac."""
    t = et(now)
    if t.weekday() >= 5 or not time(9, 25) <= t.time() < time(16, 0) or st.get("morning") == t.date().isoformat():
        return
    st["morning"] = t.date().isoformat()
    if discord_running():
        notify.push("Edward relay is on", "Watching VIP #alerts and free #trade-ideas.", priority=-1)
    else:
        notify.push("⚠️ Discord isn't open on your Mac", "The Edward relay can't see his posts until Discord is open.",
                    priority=1)


class KeepAwake:
    """Optional: stop the Mac idling to sleep on weekdays 9:00 AM - 4:15 PM ET (screen still sleeps and locks)."""

    def __init__(self):
        self.proc = None

    def update(self, now):
        t = et(now)
        want = t.weekday() < 5 and time(9, 0) <= t.time() < time(16, 15)
        if want and (self.proc is None or self.proc.poll() is not None):
            self.proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
        elif not want and self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            self.proc = None


def run(args):
    st = load(STATE, {})
    if not notify.channels(notify.config()):
        print("No phone channel set up yet (run `relay setup`). Posts will only be logged.")
    copier = None if args.no_copy else Copier(Alpaca())
    try:
        if args.fresh or "last_rec_id" not in st:
            st["last_rec_id"] = max_rec_id()  # start from now; never replay old notifications
    except sqlite3.Error:
        raise SystemExit(CANT_READ)
    awake = KeepAwake() if args.keep_awake else None
    failures, beat = 0, 0.0
    print(f"Edward relay running (pid {os.getpid()}): VIP #alerts + free #trade-ideas -> phone"
          f"{'' if copier is None else ' + paper copy'}. Ctrl-C stops it.", flush=True)
    while True:
        now = datetime.now(timezone.utc)
        try:
            posts, st["last_rec_id"] = read_new(st["last_rec_id"])
            failures = 0
        except sqlite3.Error as exc:
            posts, failures = [], failures + 1
            if failures in (1, 300):
                print(f"{now:%H:%M:%S} notification list unreadable: {exc}", flush=True)
            if failures == 300:
                notify.push("⚠️ Edward relay can't read notifications", CANT_READ, priority=1)
        seen = st.setdefault("seen", [])
        for post in posts:
            if post["msg_id"] in seen:
                continue
            st["seen"] = seen = (seen + [post["msg_id"]])[-500:]
            rec = handle(post, copier, now)
            print(f"{et(now):%H:%M:%S} {rec['channel']} {rec['kind']}: {rec['text'][:80]!r}"
                  f" push={rec.get('pushed')} {rec.get('copy', '')}", flush=True)
        if copier is not None:
            try:
                copier.tick(now)
            except Exception as exc:
                print(f"{et(now):%H:%M:%S} copier check failed: {type(exc).__name__}: {exc}", flush=True)
        morning_check(st, now)
        if awake:
            awake.update(now)
        if posts or clock.monotonic() - beat > 30:
            st["heartbeat"], beat = now.isoformat(), clock.monotonic()
            save(STATE, st)
        clock.sleep(1)


# ---- other commands ----------------------------------------------------------------------------------------
def write_env(values, path=None):
    """Set KEY=value lines in the owner-only .env.edward, keeping every other line."""
    path = Path(path or notify.ENV)
    lines = path.read_text().splitlines() if path.exists() else []
    lines = [ln for ln in lines if ln.split("=", 1)[0].strip() not in values]
    lines += [f"{k}={v}" for k, v in values.items()]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def setup(args):
    cfg = notify.config()
    print("Pushover: open the Pushover app for your user key; create an app token at https://pushover.net/apps/build.\n"
          "Input is hidden. Press Enter to keep what's saved (or skip).")
    user = getpass("Pushover user key: ").strip() or cfg.get("PUSHOVER_USER_KEY", "")
    token = getpass("Pushover app API token: ").strip() or cfg.get("PUSHOVER_APP_TOKEN", "")
    topic = cfg.get("NTFY_TOPIC", "")
    if args.ntfy and not topic:
        topic = "edward-" + secrets.token_hex(12)
    write_env({"PUSHOVER_USER_KEY": user, "PUSHOVER_APP_TOKEN": token, "NTFY_TOPIC": topic})
    print("Saved to .env.edward (owner-only). Channels ready:", notify.channels(notify.config()) or "none")
    if topic:
        print(f"ntfy: in the ntfy app, subscribe to topic  {topic}  on ntfy.sh (keep this name private).")


def test_push(args):
    title, message, priority = push_text(parse("$QQQ 720 PUT 10/19 @ 0.73 0DTE LOTTO", datetime.now(NY).date()), "vip")
    print(notify.push("TEST " + title, "This is a test of the Edward relay.\n\n" + message, priority=priority,
                      url="https://discord.com/channels/1180233578467053659/1324790086885314670",
                      url_title="Open VIP #alerts"))


def paste(args):
    now = datetime.now(timezone.utc)
    channel = next(k for k, v in CHANNELS.items() if v[0] == args.channel)
    post = {"rec_id": 0, "msg_id": f"paste-{int(now.timestamp())}", "channel": channel, "label": args.channel,
            "author": "pasted", "text": args.text, "posted": now,
            "link": f"https://discord.com/channels/{CHANNELS[channel][1]}/{channel}"}
    copier = None if (args.no_copy or args.dry_run) else Copier(Alpaca())
    rec = handle(post, copier, now, dry=args.dry_run)
    if not args.dry_run:
        print(json.dumps({k: rec.get(k) for k in ("kind", "pushed", "copy")}, indent=1))


def scan(args):
    try:
        with connect() as con:
            rows = con.execute("select r.rec_id, r.data from record r join app a on a.app_id = r.app_id "
                               "where lower(a.identifier) = 'com.hnc.discord' order by r.rec_id").fetchall()
    except sqlite3.Error:
        raise SystemExit(CANT_READ)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    posts = [p for p in (decode(r, b) for r, b in rows) if p and p["posted"] >= cutoff]
    print(f"{len(rows)} Discord notifications in the list; {len(posts)} from Edward's two channels "
          f"in the last {args.hours} h.")
    for p in posts:
        ev = parse(p["text"], et(p["posted"]).date())
        print(f"{et(p['posted']):%m/%d %H:%M} {p['label']:4} {ev['kind']:6} {clean(p['text'])[:90]}")


def status(args):
    st = load(STATE, {})
    beat = st.get("heartbeat")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds() if beat else None
    print(f"relay heartbeat: {'never' if age is None else f'{age:.0f} s ago'}"
          f"{'  (NOT RUNNING?)' if age is None or age > 120 else ''}; Discord open: {discord_running()}; "
          f"phone channels: {notify.channels(notify.config()) or 'none'}")
    if EVENTS.exists():
        print("\nlast posts:")
        for line in EVENTS.read_text().splitlines()[-10:]:
            r = json.loads(line)
            print(f"  {et(datetime.fromisoformat(r['posted'])):%m/%d %H:%M} {r['channel']:4} {r['kind']:6} "
                  f"{r['text'][:70]!r} {r.get('copy', '')}")
    copier = Copier(None)
    print("\npaper copies:", json.dumps(copier.report(datetime.now(timezone.utc)), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--no-copy", action="store_true", help="alerts only, no paper orders")
    r.add_argument("--keep-awake", action="store_true", help="keep the Mac from idling to sleep in market hours")
    r.add_argument("--fresh", action="store_true", help="ignore anything already in the notification list")
    s = sub.add_parser("setup")
    s.add_argument("--ntfy", action="store_true", help="also create a private ntfy topic (free alternative)")
    sub.add_parser("test-push")
    p = sub.add_parser("paste")
    p.add_argument("text")
    p.add_argument("--channel", choices=["vip", "free"], default="vip")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-copy", action="store_true")
    sc = sub.add_parser("scan")
    sc.add_argument("--hours", type=float, default=24)
    sub.add_parser("status")
    a = ap.parse_args()
    {"run": run, "setup": setup, "test-push": test_push, "paste": paste, "scan": scan, "status": status}[a.cmd](a)


if __name__ == "__main__":
    main()
