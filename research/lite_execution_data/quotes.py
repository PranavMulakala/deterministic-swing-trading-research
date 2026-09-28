"""Offline nanosecond-aware quote feasibility, not an execution/P&L simulator."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from statistics import median

STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,9}))?(Z|[+-]\d\d:\d\d)$")


def nanos(value):
    match = STAMP.fullmatch(value)
    if not match:
        raise ValueError("Invalid timezone-aware nanosecond timestamp")
    base, fraction, offset = match.groups()
    dt = datetime.fromisoformat(base + ("+00:00" if offset == "Z" else offset)).astimezone(timezone.utc)
    delta = dt - datetime(1970,1,1,tzinfo=timezone.utc)
    return (delta.days*86400+delta.seconds)*1000000000 + int((fraction or "0").ljust(9,"0"))


def quote_at(rows, cutoff, raw_limit):
    previous, candidates = None, []
    for row in rows:
        stamp = nanos(row["t"])
        if previous is not None and stamp < previous:
            raise ValueError("Out-of-order quote stream")
        previous = stamp
        if stamp <= cutoff:
            candidates.append((stamp,row))
    if not candidates:
        return {"status":"UNKNOWN_NO_PRIOR_QUOTE"}
    stamp, row = candidates[-1]
    if cutoff-stamp > 1000000000:
        return {"status":"UNKNOWN_STALE_QUOTE", "age_ns":cutoff-stamp}
    tied = [r for t,r in candidates if t == stamp]
    if len({(r.get("bp"),r.get("ap"),r.get("bs"),r.get("as")) for r in tied}) > 1:
        return {"status":"UNKNOWN_SAME_TIMESTAMP_ORDERING"}
    if row.get("c") != ["R"]:
        return {"status":"UNKNOWN_NONREGULAR_CONDITION"}
    values = [row.get(k) for k in ("bp","ap","bs","as")]
    if any(type(v) not in (float,int) or not Decimal(str(v)).is_finite() or v <= 0 for v in values):
        return {"status":"UNKNOWN_INVALID_QUOTE"}
    bid, ask, _, _ = values
    if bid > ask:
        return {"status":"UNKNOWN_CROSSED_QUOTE"}
    spread = 10000*(ask-bid)/((ask+bid)/2)
    return {"status":"OBSERVED", "quote_time":row["t"], "age_ns":cutoff-stamp,
            "bid":bid, "ask":ask, "full_spread_bps":spread, "half_spread_bps":spread/2,
            "ask_within_raw_limit":ask <= raw_limit,
            "note":"Available quote is not proof of order fill or broker delivery timing"}


def analyze(study, folder):
    signals = [r for r in study["capital_diagnostics"] if r["variant"]=="vwap_retest" and r["status"]=="valid_signal"]
    windows = study["quote_windows"]
    if len(signals) != len(windows):
        raise ValueError("Signal/window count mismatch")
    items, provenance = [], []
    for index,(signal,window) in enumerate(zip(signals,windows)):
        path = folder/f"quotes_{index:03}.json"
        raw = path.read_bytes()
        payload = json.loads(raw)
        if payload["path"] != "/v2/stocks/LITE/quotes" or payload["query"].get("feed") != "sip":
            raise ValueError("Wrong quote source")
        if any(payload["query"].get(k) != v for k,v in window.items()):
            raise ValueError("Quote window mismatch")
        left,right = nanos(window["start"]),nanos(window["end"])
        if any(not left <= nanos(r["t"]) <= right for r in payload["rows"]):
            raise ValueError("Quote outside requested window")
        readings = {}
        for label,delay in (("100ms",100000000),("1s",1000000000),("2s",2000000000)):
            readings[label] = quote_at(payload["rows"],nanos(signal["signal_time"])+delay,signal["raw_limit"]) if payload["complete"] is True else {"status":"UNKNOWN_TRUNCATED_WINDOW"}
        items.append({"date":signal["date"],"signal_time":signal["signal_time"],
                      "raw_limit":signal["raw_limit"],"records":len(payload["rows"]),"readings":readings})
        provenance.append({"file":path.name,"sha256":hashlib.sha256(raw).hexdigest()})
    summary = {}
    for label in ("100ms","1s","2s"):
        readings = [r["readings"][label] for r in items]
        measured = [r for r in readings if r["status"]=="OBSERVED"]
        summary[label] = {"status_counts":dict(Counter(r["status"] for r in readings)),
                          "asks_within_original_limit":sum(r["ask_within_raw_limit"] for r in measured),
                          "median_full_spread_bps":median(r["full_spread_bps"] for r in measured) if measured else None,
                          "max_full_spread_bps":max((r["full_spread_bps"] for r in measured),default=None)}
    return {"status":"DIAGNOSTIC_ONLY", "signal_count":len(signals), "summary":summary,"observations":items,"provenance":provenance}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",type=Path,required=True)
    parser.add_argument("--quotes",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    raw_study = args.study.read_bytes()
    result = analyze(json.loads(raw_study),args.quotes)
    result["study_sha256"] = hashlib.sha256(raw_study).hexdigest()
    result["analyzer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open("x") as handle:
        handle.write(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"signal_count":result["signal_count"],"summary":result["summary"]},indent=2))
