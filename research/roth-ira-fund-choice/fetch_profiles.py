"""Cache Alpha Vantage ETF_PROFILE (expense ratio, holdings, sectors) and GLOBAL_QUOTE for the Roth study.

Reuses the 401(k) analyzer's key loader (.env.news; never printed). Usage: python fetch_profiles.py
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "401k-fund-choice"))
import fetch  # noqa: E402

OUT = HERE / "data" / "profiles"
ETFS = ["VT", "VTI", "VXUS", "VOO", "QQQM", "VUG", "SCHG", "SPMO", "SMH", "AVUV"]
QUOTES = ["LITE", "MU", "VT", "VTI", "VXUS", "VOO"]


def get(params, key):
    q = urllib.parse.urlencode({**params, "apikey": key})
    with urllib.request.urlopen(f"{fetch.URL}?{q}", timeout=30) as r:
        return json.load(r)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = fetch.api_key()
    jobs = [("ETF_PROFILE", s) for s in ETFS] + [("GLOBAL_QUOTE", s) for s in QUOTES]
    for fn, sym in jobs:
        path = OUT / f"{fn}_{sym}.json"
        if path.exists():
            continue
        for attempt in range(3):
            data = get({"function": fn, "symbol": sym}, key)
            if not any(k in data for k in ("Note", "Information")):
                break
            time.sleep(5)
        if any(k in data for k in ("Note", "Information", "Error Message")):
            print(fn, sym, "no data:", {k: v for k, v in data.items() if k in ("Note", "Information", "Error Message")})
            continue
        path.write_text(json.dumps(data))
        print(fn, sym, "ok")
        time.sleep(1.5)


if __name__ == "__main__":
    main()
