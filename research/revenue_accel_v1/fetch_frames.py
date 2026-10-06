"""Test #20 data: SEC EDGAR XBRL frames for quarterly and annual revenue, 2015-2026 (output/REVENUE_ACCELERATION_TEST_PLAN_20261005.md).

  PYTHONPATH=src:. .venv/bin/python -m research.revenue_accel_v1.fetch_frames

Free official data (data.sec.gov), the owner's approved User-Agent (research/ep_test_v1/fetch_edgar.py), about 4 requests
a second. Keeps only each frame's rows (cik, start, end, val) in outputs/revenue_accel_data/ (gitignored), plus SEC's
ticker list for matching companies to price files. Resumable: frames already saved are skipped.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from research.ep_test_v1.fetch_edgar import STATS, TICKERS_URL, get_json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/revenue_accel_data"
CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax"]
QUARTERS = [f"CY{y}Q{q}" for y in range(2015, 2027) for q in range(1, 5) if (y, q) <= (2026, 2)]
YEARS = [f"CY{y}" for y in range(2015, 2026)]


def path_for(concept, period):
    return OUT / "frames" / f"{concept}_{period}.json.gz"


def main():
    (OUT / "frames").mkdir(parents=True, exist_ok=True)
    done, missing = 0, []
    for concept in CONCEPTS:
        for period in QUARTERS + YEARS:
            p = path_for(concept, period)
            if p.exists():
                done += 1
                continue
            frame = get_json(f"https://data.sec.gov/api/xbrl/frames/us-gaap/{concept}/USD/{period}.json")
            rows = [[r["cik"], r.get("start"), r["end"], r["val"]] for r in (frame or {}).get("data", [])]
            if frame is None:
                missing.append(f"{concept} {period}")
            with gzip.open(p, "wt") as f:
                json.dump(rows, f)
            done += 1
    tickers = get_json(TICKERS_URL)
    with gzip.open(OUT / "company_tickers.json.gz", "wt") as f:
        json.dump(tickers, f)
    print(json.dumps({"frames": done, "not_on_sec": missing, **STATS}))


if __name__ == "__main__":
    main()
