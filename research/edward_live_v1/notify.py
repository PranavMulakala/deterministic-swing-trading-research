"""Phone alerts for the Edward relay: Pushover and/or ntfy. Only the relay sends here, so only Edward's two channels
ever reach these apps; that is what lets them through Do Not Disturb while Discord itself stays silent.

  - Pushover: priority 1-2 become iOS Critical Alerts once "Critical Alerts" is on in the Pushover app (they sound
    through Do Not Disturb and the silent switch). Priority 2 repeats every 60 s until tapped, for up to 5 minutes.
  - ntfy (free, no account): add the ntfy app to the Do Not Disturb focus's allowed apps.
Keys live in the owner-only `.env.edward` (gitignored): PUSHOVER_APP_TOKEN, PUSHOVER_USER_KEY, NTFY_TOPIC,
optional NTFY_SERVER, and the cloud inbox's EDWARD_INBOX_TOPIC / EDWARD_INBOX_KEY. Values are never printed.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env.edward"
KEYS = ("PUSHOVER_APP_TOKEN", "PUSHOVER_USER_KEY", "NTFY_TOPIC", "NTFY_SERVER", "EDWARD_INBOX_TOPIC", "EDWARD_INBOX_KEY")
NTFY_PRIORITY = {2: 5, 1: 5, 0: 3, -1: 2, -2: 1}


def config(path=ENV):
    vals = {}
    if Path(path).exists():
        for line in Path(path).read_text().splitlines():
            m = re.fullmatch(r"\s*(?:export\s+)?([A-Z_]+)\s*=\s*(.*?)\s*", line)
            if m and m[1] in KEYS and m[2].strip("\"'"):
                vals[m[1]] = m[2].strip("\"'")
    return vals


def channels(cfg):
    out = []
    if cfg.get("PUSHOVER_APP_TOKEN") and cfg.get("PUSHOVER_USER_KEY"):
        out.append("pushover")
    if cfg.get("NTFY_TOPIC"):
        out.append("ntfy")
    return out


def push(title, message, priority=1, url=None, url_title=None, cfg=None, opener=urllib.request.urlopen):
    """Send to every configured channel; returns {channel: "ok" | error text}. Never raises."""
    cfg = config() if cfg is None else cfg
    result = {}
    if "pushover" in channels(cfg):
        form = {"token": cfg["PUSHOVER_APP_TOKEN"], "user": cfg["PUSHOVER_USER_KEY"], "title": title[:250],
                "message": message[:1024], "priority": str(priority)}
        if priority == 2:
            form.update(retry="60", expire="300")
        if url:
            form.update(url=url[:512], url_title=(url_title or url)[:100])
        req = urllib.request.Request("https://api.pushover.net/1/messages.json", method="POST",
                                     data=urllib.parse.urlencode(form).encode())
        result["pushover"] = _send(req, opener)
    if "ntfy" in channels(cfg):
        body = {"topic": cfg["NTFY_TOPIC"], "title": title, "message": message,
                "priority": NTFY_PRIORITY.get(priority, 3), "tags": ["rotating_light"] if priority == 2 else []}
        if url:
            body["click"] = url
        req = urllib.request.Request(cfg.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/"), method="POST",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        result["ntfy"] = _send(req, opener)
    return result


def _send(req, opener):
    try:
        with opener(req, timeout=10) as r:
            return "ok" if 200 <= r.status < 300 else f"HTTP {r.status}"
    except Exception as exc:  # A failed push must never stop the relay; the event log keeps the error.
        return f"{type(exc).__name__}: {str(exc)[:120]}"
