"""Bounded historical GET-only acquisition. No strategy or account operations."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

from swingbot.alpaca_paper import AlpacaPaperClient
from swingbot.paper_cli import _load_env

ROOT = Path(__file__).resolve().parents[2]
SYMBOLS = ("LITE", "COHR", "CIEN", "FN", "AAOI")
CONTROLS = ("SPY", "QQQ")
JOBS = tuple((s, t) for s in SYMBOLS for t in (1, 5)) + tuple((s, 5) for s in CONTROLS)
START = "2025-11-01T00:00:00Z"
END = "2026-09-05T00:00:00Z"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as handle:
        handle.write(raw)
    return {"file": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def bar_query(step):
    if step not in (1, 5):
        raise ValueError("Unsupported timeframe")
    return {"start": START, "end": END, "feed": "sip", "adjustment": "raw",
            "asof": "2026-09-04", "timeframe": f"{step}Min", "sort": "asc", "limit": 10000}


class HistoricalClient(AlpacaPaperClient):
    def _request(self, method, path, *, data_api=False, query=None, **kwargs):
        allowed = {f"/v2/stocks/{s}/bars" for s in SYMBOLS + CONTROLS}
        if method != "GET" or kwargs or (path not in allowed if data_api else path != "/v2/calendar"):
            raise ValueError("Only historical bars and calendar GETs are permitted")
        return super()._request(method, path, data_api=data_api, query=query)


def paged(client, symbol, step, max_pages=80, pause=time.sleep):
    if (symbol, step) not in JOBS or max_pages < 1:
        raise ValueError("Unsupported collection job")
    query = bar_query(step)
    path = f"/v2/stocks/{symbol}/bars"
    token = None
    seen = set()
    rows = []
    began = datetime.now(timezone.utc).isoformat()
    for page in range(1, max_pages + 1):
        pause(0.35)
        reply = client._request("GET", path, data_api=True,
                                query={**query, **({"page_token": token} if token else {})})
        if not isinstance(reply, dict) or reply.get("symbol") != symbol or not isinstance(reply.get("bars"), list):
            raise ValueError("Invalid bars response or symbol")
        rows.extend(reply["bars"])
        token = reply.get("next_page_token")
        if token is None:
            return {"complete": True, "path": path, "query": query, "pages": page, "rows": rows,
                    "requested_at": began, "received_at": datetime.now(timezone.utc).isoformat()}
        if not isinstance(token, str) or not token or token in seen or not reply["bars"]:
            raise ValueError("Stalled or malformed pagination")
        seen.add(token)
    raise ValueError("Pagination limit reached; complete snapshot not obtained")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    _load_env(ROOT / ".env")
    client = HistoricalClient(os.environ.get("ALPACA_PAPER_API_KEY", ""),
                              os.environ.get("ALPACA_PAPER_API_SECRET", ""), timeout=30)
    manifest = {"collector_sha256": digest(__file__), "jobs": JOBS,
                "started_at": datetime.now(timezone.utc).isoformat(), "files": [], "errors": []}
    try:
        calendar = client._request("GET", "/v2/calendar", query={"start": "2025-11-01", "end": "2026-09-04"})
        if not isinstance(calendar, list) or not calendar:
            raise ValueError("Calendar unavailable")
        manifest["files"].append(save(args.output / "calendar.json", calendar))
        for symbol, step in JOBS:
            result = paged(client, symbol, step)
            manifest["files"].append(save(args.output / f"{symbol}_{step}Min.json", result))
            print(f"{symbol} {step}Min: {len(result['rows'])} rows, {result['pages']} pages complete", flush=True)
    except Exception as exc:
        # Provider exceptions may contain request details: never print their body or credentials.
        manifest["errors"].append({"type": type(exc).__name__, "message": "Acquisition failed; no provider error body retained"})
    manifest["complete"] = not manifest["errors"] and len(manifest["files"]) == len(JOBS) + 1
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    save(args.output / "manifest.json", manifest)
    print(json.dumps({"complete": manifest["complete"], "files": len(manifest["files"]), "errors": manifest["errors"]}))
    return 0 if manifest["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
