"""LITE vs SMH (and SPY, QQQ) over several windows, plus the LITE-like stocks' past returns (hindsight, descriptive only).

  PYTHONPATH=src:. .venv/bin/python -m research.lite_like_screener_v1.lite_vs_smh

Fresh Alpaca SIP daily bars (adjustment=all, so dividends are included), Jan 2016 to the latest close. Read-only.
Writes output/lite-vs-smh-20261005.json.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/lite-vs-smh-20261005.json"
CORE = ["LITE", "SMH", "SPY", "QQQ"]


def fetch_daily(symbols):
    from research.lite_dip_history_v1.run import DATA, fetch
    from research.lite_paper_bot_v1.bot import credentials
    key, secret = credentials()
    end = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {}
    for i in range(0, len(symbols), 50):
        q = {"symbols": ",".join(symbols[i:i + 50]), "timeframe": "1Day", "feed": "sip", "adjustment": "all",
             "sort": "asc", "limit": 10000, "start": "2016-01-01T00:00:00Z", "end": end}
        token = None
        while True:
            if token:
                q["page_token"] = token
            page = fetch(f"{DATA}/v2/stocks/bars?{urllib.parse.urlencode(q)}", key, secret)
            for s, rows in (page.get("bars") or {}).items():
                out.setdefault(s, []).extend((r["t"][:10], r["c"]) for r in rows)
            token = page.get("next_page_token")
            time.sleep(0.35)
            if not token:
                break
    return {s: sorted(v) for s, v in out.items()}


def window_stats(series, start):
    """Growth, yearly rate, worst drop and growth per unit of drop from the last close on/before `start`."""
    pts = [p for p in series if p[0] > start]
    before = [p for p in series if p[0] <= start] or series[:1]      # no earlier close: start at the first one
    if not pts:
        return None
    base = before[-1][1]
    path = [base] + [c for _, c in pts]
    peak, worst = base, 0.0
    for c in path:
        peak = max(peak, c)
        worst = min(worst, c / peak - 1)
    years = (datetime.fromisoformat(pts[-1][0]) - datetime.fromisoformat(before[-1][0])).days / 365.25
    total = path[-1] / base - 1
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 else None
    moves = [abs(path[i] / path[i - 1] - 1) for i in range(1, len(path))]
    return {"from": before[-1][0], "to": pts[-1][0], "total_pct": round(100 * total), "per_year_pct": round(100 * cagr, 1),
            "worst_drop_pct": round(100 * worst), "growth_per_drop": round(cagr / abs(worst), 2) if worst else None,
            "avg_daily_move_pct": round(100 * statistics.mean(moves), 2)}


def calendar_years(series):
    out, by = {}, {}
    for d, c in series:
        by.setdefault(d[:4], []).append(c)
    years = sorted(by)
    for n, y in enumerate(years[1:], 1):
        out[y] = round(100 * (by[y][-1] / by[years[n - 1]][-1] - 1))
    return out


def main():
    screen = json.loads((ROOT / "output/volatile-stocks-screen-20261005.json").read_text())
    peers = [s for s in screen["stocks"] if s != "LITE"]
    data = fetch_daily(CORE + ["MU"] + peers)
    last = data["SPY"][-1][0]
    y = int(last[:4])
    windows = {"1 year": f"{y - 1}{last[4:]}", "3 years": f"{y - 3}{last[4:]}", "5 years": f"{y - 5}{last[4:]}",
               "since 2016": "2015-12-31"}
    core = {s: {w: window_stats(data[s], start) for w, start in windows.items()} for s in CORE + ["MU"]}
    for s in CORE + ["MU"]:                                            # the split that matters: before 2025 vs after
        core[s]["2016 to end-2024"] = window_stats([p for p in data[s] if p[0] <= "2024-12-31"], "2015-12-31")
        core[s]["2025 to now"] = window_stats(data[s], "2024-12-31")
        core[s]["since 2020 (post-COVID, main)"] = window_stats(data[s], "2019-12-31")
        core[s]["2020 to end-2024"] = window_stats([p for p in data[s] if p[0] <= "2024-12-31"], "2019-12-31")
    years = {s: calendar_years(data[s]) for s in CORE}
    monthly = {}
    for s in ("LITE", "SMH", "SPY"):
        pts, seen = [], set()
        for d, c in data[s]:
            if d > "2019-12-31" and d[:7] not in seen:
                seen.add(d[:7])
                pts.append((d, c))
        if pts[-1][0] != data[s][-1][0]:
            pts.append(data[s][-1])
        base = [c for d, c in data[s] if d <= "2019-12-31"][-1]
        monthly[s] = [[d[:7], round(10_000 * c / base)] for d, c in pts]
    peer_rows = {}
    for s in peers + ["LITE", "MU"]:
        if s in data:
            peer_rows[s] = {w: window_stats(data[s], windows[w]) for w in ("1 year", "3 years", "5 years")}
            peer_rows[s]["since 2020"] = window_stats(data[s], "2019-12-31")
    out = {"last_close": last, "windows": windows, "core": core, "calendar_years": years,
           "growth_of_10k_monthly_since_2020": monthly, "lite_like": peer_rows}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    for s in CORE + ["MU"]:
        print(s, json.dumps({w: (v and {k: v[k] for k in ("total_pct", "per_year_pct", "worst_drop_pct", "growth_per_drop")})
                             for w, v in core[s].items()}))
    print("calendar years:", json.dumps(years))


if __name__ == "__main__":
    main()
