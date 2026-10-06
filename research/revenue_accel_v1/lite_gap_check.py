"""Test #20, written AFTER the result, information only (does not change the verdict).

SEC's frames API never placed LITE's fiscal-2024 annual revenue (Jul 2023 - Jun 2024, $1,359.2M in the 10-K filed
Aug 21, 2024) in any calendar-year frame, so its Apr-Jun 2024 quarter was missing and LITE couldn't be scored from
Sep 2025 to Apr 2026. This re-runs the main rule with that one quarter restored from LITE's own SEC facts
(outputs/revenue_accel_data/lite_companyconcept.json.gz: $1,359.2M - $1,050.9M for the first three quarters).

  PYTHONPATH=src:. .venv/bin/python -m research.revenue_accel_v1.lite_gap_check
"""
from __future__ import annotations

import gzip
import json

from research.breakout_test_v1.backtest import DATA, load
from research.momentum_lite_like_v1.fetch_etfs import ETFS, path_for as etf_path
from research.revenue_accel_v1.backtest import MAIN_START, ROOT, company_tickers, evaluate, picks_at, prepare
from research.revenue_accel_v1.fetch_frames import OUT as RAW
from research.revenue_accel_v1.revenue import load_frames, quarterly

LITE_CIK = 1633978


def main():
    stocks = {p.name[:-7]: prepare(load(p.name[:-7])) for p in sorted(DATA.glob("*.csv.gz")) if p.name != "SPY.csv.gz"}
    etfs = {}
    for s in ETFS:
        with gzip.open(etf_path(s), "rt") as f:
            etfs[s] = prepare(json.load(f))
    with gzip.open(RAW / "lite_companyconcept.json.gz", "rt") as f:
        facts = json.load(f)["RevenueFromContractWithCustomerExcludingAssessedTax"]
    year = next(r["val"] for r in facts if (r.get("start"), r["end"], r["form"]) == ("2023-07-02", "2024-06-29", "10-K"))
    nine = next(r["val"] for r in facts if (r.get("start"), r["end"]) == ("2023-07-02", "2024-03-30"))
    quarters = quarterly(load_frames())
    quarters[LITE_CIK] = [dict(s) for s in quarters[LITE_CIK]]
    quarters[LITE_CIK][0]["2024Q2"] = ("2024-06-29", year - nine)
    tickers = company_tickers(set(stocks))
    res, _, log = evaluate({**stocks, **etfs}, etfs["SPY"]["date"], MAIN_START,
                           lambda day: picks_at(day, stocks, quarters, tickers))
    held = [e["formation"] for e in log if "LITE" in [p[0] for p in e["picks"]]]
    out = {"note": "after the result, information only", "lite_apr_jun_2024_revenue": year - nine,
           "strategy": res["strategy"], "spy": res["spy"], "halves": res["halves"], "checks": res["checks"],
           "passes": res["passes"], "lite_held_after_formations": held}
    (ROOT / "output/revenue-acceleration-lite-gap-check.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
