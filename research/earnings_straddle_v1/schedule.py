"""Turn events.json into test #7's entry/exit schedule using the NYSE trading calendar (Alpaca, read-only).

  PYTHONPATH=src:. .venv/bin/python -m research.earnings_straddle_v1.schedule

L = last close before the report (post-market: the report day; pre-market: the trading day before).
E = 3 trading days before L. Writes schedule.json: [[symbol, E, L, timing, report_date], ...] sorted by E.
"""
from __future__ import annotations

import json
from pathlib import Path

from research.lite_dip_history_v1.run import PAPER, fetch
from research.lite_paper_bot_v1.bot import credentials

HERE = Path(__file__).resolve().parent


def main():
    key, secret = credentials()
    days = [d["date"] for d in fetch(f"{PAPER}/v2/calendar?start=2011-11-01&end=2026-10-31", key, secret)]
    events = json.loads((HERE / "events.json").read_text())
    rows = []
    for symbol, items in events.items():
        for report, timing in items:
            before = [d for d in days if d < report]
            last = report if (timing == "post" and report in days) else before[-1]
            i = days.index(last)
            rows.append([symbol, days[i - 3], last, timing, report])
    rows.sort(key=lambda r: (r[1], r[0]))
    (HERE / "schedule.json").write_text(json.dumps(rows) + "\n")
    print(len(rows), "events;", rows[0], rows[-1])


if __name__ == "__main__":
    main()
