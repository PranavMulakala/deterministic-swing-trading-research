"""Download Alpaca SIP 5-minute bars for QQQ and SPY (test #8, output/CRT_SWEEP_TEST_PLAN_20261005.md). Research only.

  PYTHONPATH=src:. .venv/bin/python -m research.crt_sweep_test_v1.fetch

Uses the LITE paper account's read-only data keys; places no orders. Caches gzip JSON under outputs/crt_sweep_data/.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from research.lite_buy_timing_v1.run import bars
from research.lite_paper_bot_v1.bot import credentials

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/crt_sweep_data"
SYMBOLS, START, END = ("QQQ", "SPY"), "2016-01-01T00:00:00Z", "2026-10-03T00:00:00Z"


def path_for(symbol):
    return DATA / f"{symbol}_5min_sip_2016-01-01_2026-10-02.json.gz"


def main():
    key, secret = credentials()
    DATA.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        out = path_for(symbol)
        if out.exists():
            print(json.dumps({"symbol": symbol, "cached": str(out)}))
            continue
        rows = bars(symbol, "5Min", START, END, key, secret, adjustment="all")
        with gzip.open(out, "wt") as handle:
            json.dump(rows, handle)
        print(json.dumps({"symbol": symbol, "bars": len(rows), "first": rows[0]["t"], "last": rows[-1]["t"]}), flush=True)


if __name__ == "__main__":
    main()
