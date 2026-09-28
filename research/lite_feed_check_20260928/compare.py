"""After-the-fact, GET-only IEX versus SIP check of the Sept 28 LITE 10:00 rule.

Written before the 10:00 observation. This is NOT the prospective decision; the
one-shot observer file is. Run only after 10:20 ET on 2026-09-28, when SIP bars
are older than the free plan's 15-minute delay:

PYTHONPATH=src .venv/bin/python -m research.lite_feed_check_20260928.compare --observation OBS.json --output NEW_DIR

For each feed it re-reads the 09:30-10:05 five-minute bars, evaluates the frozen
decision() against that feed's own prior 20 mornings from the verified refresh,
and records each condition's margin. The 10:00 bar low is reported only as the
replay's bar-cross proxy, never as a fill. SIP quotes for 10:00-10:05 are fetched
only if the observer proposed a signal. No account, position or order endpoint.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from research.lite_execution_data.collect import save
from research.lite_funded_comparison_v1.run import D
from research.lite_reversal_v1.experiment import timestamp
from research.lite_volume_rebound_v1.observe_monday import MONDAY, NY
from research.lite_volume_rebound_v1.refresh import (
    BAR_PATH, calendar_sessions, client_from_local_keys, validate_feed,
)
from research.lite_volume_rebound_v1.run import decision

EARLIEST = datetime(2026, 9, 28, 10, 20, tzinfo=NY)
QUOTE_PATH = "/v2/stocks/LITE/quotes"
MAX_QUOTE_PAGES = 20
BARS_QUERY = {"adjustment": "raw", "timeframe": "5Min", "start": "2026-09-28T13:30:00Z",
              "end": "2026-09-28T14:04:59Z", "sort": "asc", "limit": 100}


def prior_mornings(folder, feed):
    """Verify every refresh hash, then return this feed's prior 20 mornings."""
    manifest = json.loads((folder / "manifest.json").read_bytes())
    names = set()
    for item in manifest.get("files", []):
        name = item.get("file")
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Unsafe refresh file")
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != item.get("sha256"):
            raise ValueError("Refresh file hash mismatch")
        names.add(name)
    if not {"report.json", "calendar.json", f"LITE_5Min_{feed}.json"}.issubset(names):
        raise ValueError("Required refresh file absent")
    report = json.loads((folder / "report.json").read_bytes())
    if report.get("status") != "COMPLETE_SIP_WITH_IEX_COVERAGE_REPORTED":
        raise ValueError("Refresh validation did not pass")
    calendar = calendar_sessions(json.loads((folder / "calendar.json").read_bytes()))
    payload = json.loads((folder / f"LITE_5Min_{feed}.json").read_bytes())
    if payload.get("feed") != feed:
        raise ValueError("Wrong refresh feed")
    _, morning, _ = validate_feed(payload, calendar)
    standard = [day for day, row in calendar.items()
                if row.get("open") == "09:30" and row.get("close") == "16:00"]
    days = standard[-20:]
    if len(days) != 20 or days[-1] != "2026-09-25" or any(day not in morning for day in days):
        raise ValueError("Missing one of the prior 20 mornings")
    return [[SimpleNamespace(**row) for row in morning[day]] for day in days], days


def today_bars(reply):
    """Six required 09:30-09:55 bars plus the optional 10:00 entry bar."""
    if not isinstance(reply, dict) or reply.get("symbol") != "LITE" or not isinstance(reply.get("bars"), list):
        raise ValueError("Wrong bar response")
    if reply.get("next_page_token"):
        raise ValueError("Bars were truncated")
    found = {}
    for row in reply["bars"]:
        dt = timestamp(row["t"])
        minute = dt.hour * 60 + dt.minute
        if dt.date().isoformat() != MONDAY or not 570 <= minute < 605 or minute % 5 or dt.second or dt.microsecond:
            raise ValueError("Out-of-window bar")
        if minute in found:
            raise ValueError("Duplicate bar")
        o, high, low, close, volume = (D(row[key]) for key in ("o", "h", "l", "c", "v"))
        if not all(v.is_finite() and v > 0 for v in (o, high, low, close, volume)) or not low <= min(o, close) <= max(o, close) <= high:
            raise ValueError("Malformed OHLCV")
        found[minute] = row
    if not set(range(570, 600, 5)).issubset(found):
        raise ValueError("Missing completed morning bar")
    return [SimpleNamespace(**found[m]) for m in range(570, 600, 5)], found.get(600)


def conditions(morning, previous):
    opening = D(morning[0].o)
    low = min(D(bar.l) for bar in morning)
    closes = [D(bar.c) for bar in morning[-3:]]
    volume = sum((D(bar.v) for bar in morning), D(0))
    baseline = sum((sum((D(bar.v) for bar in prior[:6]), D(0)) for prior in previous), D(0)) / 20
    found = decision(morning, previous)
    return {"open_0930": str(opening), "lowest_low": str(low),
            "dip_pct_vs_open": str((low / opening - 1) * 100), "dip_1pct_met": low <= opening * D("0.99"),
            "last_three_closes": [str(c) for c in closes],
            "rising_met": closes[0] < closes[1] < closes[2], "still_below_open_met": closes[2] < opening,
            "morning_volume": str(volume), "prior_20_mean_volume": str(baseline),
            "volume_ratio": str(volume / baseline), "volume_1_5x_met": volume >= D("1.5") * baseline,
            "decision_limit": None if found is None else str(found["limit"])}


def entry_bar_proxy(bar, limit):
    """Replay's optimistic bar-cross proxy only; never evidence of a queue fill."""
    if bar is None or limit is None:
        return None
    crossed = D(bar["l"]) <= D(limit)
    return {"bar_0100_ohlc": {k: str(bar[k]) for k in ("o", "h", "l", "c")}, "low_at_or_below_limit": crossed,
            "replay_fill_proxy": str(min(D(bar["o"]), D(limit))) if crossed else None}


def quote_check(client, limit, output, files):
    query = {"feed": "sip", "start": "2026-09-28T14:00:00Z", "end": "2026-09-28T14:05:00Z", "limit": 10000}
    token, seen, count, best, first_at_or_below = None, set(), 0, None, None
    for page in range(1, MAX_QUOTE_PAGES + 1):
        reply = client._request("GET", QUOTE_PATH, data_api=True,
                                query={**query, **({"page_token": token} if token else {})})
        if not isinstance(reply, dict) or reply.get("symbol") != "LITE" or not isinstance(reply.get("quotes"), list):
            raise ValueError("Wrong quote response")
        files.append(save(output / f"quotes_sip_page_{page:02}.json", reply))
        for row in reply["quotes"]:
            ask = D(row.get("ap", 0))
            if ask <= 0:
                continue
            count += 1
            best = ask if best is None else min(best, ask)
            if first_at_or_below is None and ask <= D(limit):
                first_at_or_below = row["t"]
        token = reply.get("next_page_token")
        if not token:
            return {"sip_quotes_with_positive_ask": count, "lowest_sip_ask": None if best is None else str(best),
                    "first_ask_at_or_below_limit": first_at_or_below, "pages": page, "complete": True}
        if token in seen:
            raise ValueError("Stalled quote pagination")
        seen.add(token)
    return {"sip_quotes_with_positive_ask": count, "lowest_sip_ask": None if best is None else str(best),
            "first_ask_at_or_below_limit": first_at_or_below, "pages": MAX_QUOTE_PAGES, "complete": False}


def execute(client, observation_path, refresh_dir, output, now=lambda: datetime.now(timezone.utc)):
    if now().astimezone(NY) < EARLIEST:
        raise ValueError("Too early: SIP bars for 09:30-10:05 are not yet older than 15 minutes")
    raw_observation = observation_path.read_bytes()
    observation = json.loads(raw_observation)
    if observation.get("date") != MONDAY or observation.get("orders_sent") != 0:
        raise ValueError("Unexpected observation file")
    limit = (observation.get("proposal") or {}).get("limit_price")
    output.mkdir(parents=True, exist_ok=False)
    files, feeds = [], {}
    for feed in ("iex", "sip"):
        previous, days = prior_mornings(refresh_dir, feed)
        reply = client._request("GET", BAR_PATH, data_api=True, query={**BARS_QUERY, "feed": feed})
        files.append(save(output / f"bars_{feed}.json", reply))
        morning, entry_bar = today_bars(reply)
        feeds[feed] = {"prior_20_first": days[0], "prior_20_last": days[-1],
                       **conditions(morning, previous), "entry_bar_vs_observer_limit": entry_bar_proxy(entry_bar, limit)}
    iex_says, sip_says = feeds["iex"]["decision_limit"] is not None, feeds["sip"]["decision_limit"] is not None
    report = {"mode": "AFTER_THE_FACT_GET_ONLY_FEED_CHECK", "orders_sent": 0, "date": MONDAY,
              "retrieved_at": now().isoformat(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "observation_file": observation_path.name,
              "observation_sha256": hashlib.sha256(raw_observation).hexdigest(),
              "observation_status": observation.get("status"), "observer_limit": limit,
              "feeds": feeds, "feeds_agree_on_signal": iex_says == sip_says,
              "quotes": quote_check(client, limit, output, files) if observation.get("status") == "SIGNAL_PROPOSAL" else None,
              "limits": "After-the-fact bars; the observer file is the prospective decision. Bar crossings and quotes are not fills."}
    files.append(save(output / "report.json", report))
    save(output / "manifest.json", {"files": files})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--refresh", type=Path, default=Path("output/lite-volume-rebound-refresh-20260927"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    report = execute(client_from_local_keys(), args.observation, args.refresh, args.output)
    print(json.dumps({key: report[key] for key in ("observation_status", "observer_limit", "feeds_agree_on_signal")}
                     | {feed: {k: report["feeds"][feed][k] for k in ("dip_1pct_met", "rising_met", "still_below_open_met",
                                                                     "volume_1_5x_met", "volume_ratio", "decision_limit")}
                        for feed in ("iex", "sip")}, indent=2))


if __name__ == "__main__":
    main()
