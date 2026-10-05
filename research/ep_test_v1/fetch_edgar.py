"""Earnings filing times for test #16 from SEC EDGAR: every 8-K with Item 2.02 ("Results of Operations and Financial
Condition") and its acceptance time, for the stocks that have candidate gap days.

  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.fetch_edgar --pilot 20   # measure size/time first
  PYTHONPATH=src:. .venv/bin/python -m research.ep_test_v1.fetch_edgar              # full run (resumable)

Free, official data (data.sec.gov submissions API). SEC fair-access rules: a User-Agent with a name and contact email
(the owner approved theirs on 2026-10-05) and at most 10 requests/second (this paces at about 4/second).
Only the extracted 8-K Item 2.02 rows are kept (outputs/ep_data/edgar/<cik>.json); raw responses are not stored.
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from urllib.request import Request, build_opener, ProxyHandler

from research.ep_test_v1.candidates import OUT_DIR

USER_AGENT = "Pranav Mulakala pranavm1104@gmail.com"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS = "https://data.sec.gov/submissions/"
CACHE = OUT_DIR / "edgar"
SINCE = "2015-12-01"
STATS = {"requests": 0, "bytes_compressed": 0, "bytes_raw": 0}


def get_json(url, pause=0.25):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    for attempt in range(6):
        try:
            with build_opener(ProxyHandler({})).open(req, timeout=60) as reply:
                body = reply.read()
                enc = reply.headers.get("Content-Encoding", "")
            STATS["requests"] += 1
            STATS["bytes_compressed"] += len(body)
            raw = gzip.decompress(body) if enc == "gzip" else body
            STATS["bytes_raw"] += len(raw)
            time.sleep(pause)
            return json.loads(raw)
        except Exception as e:
            if getattr(e, "code", None) == 404:
                time.sleep(pause)
                return None
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed 6 times: {url}")


def norm(ticker):
    return ticker.upper().replace(".", "-").replace("/", "-")


def earnings_rows(cols):
    """8-K rows whose items include 2.02, as [acceptanceDateTime, filingDate, items] (amendments excluded)."""
    out = []
    for form, items, acc, filed in zip(cols["form"], cols["items"], cols["acceptanceDateTime"], cols["filingDate"]):
        if form == "8-K" and "2.02" in [i.strip() for i in (items or "").split(",")]:
            out.append([acc, filed, items])
    return out


def company(cik):
    path = CACHE / f"{cik}.json"
    if path.exists():
        return json.loads(path.read_text())
    sub = get_json(f"{SUBMISSIONS}CIK{cik:010d}.json")
    if sub is None:
        result = {"cik": cik, "rows": [], "error": "404"}
    else:
        recent = sub["filings"]["recent"]
        rows = earnings_rows(recent)
        oldest = min(recent["filingDate"]) if recent["filingDate"] else "9999"
        if oldest > SINCE:
            for f in sub["filings"].get("files", []):
                if f.get("filingTo", "9999") >= SINCE:
                    older = get_json(SUBMISSIONS + f["name"])
                    if older:
                        rows += earnings_rows(older)
        result = {"cik": cik, "name": sub.get("name"), "rows": sorted(rows)}
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    args = ap.parse_args()
    needed = sorted({s for v in json.loads((OUT_DIR / "candidates.json").read_text())["by_date"].values() for s in v})
    mapping = {norm(r["ticker"]): int(r["cik_str"]) for r in get_json(TICKERS_URL).values()}
    todo = needed[:args.pilot] + ["AAPL"] if args.pilot else needed   # AAPL: checks the acceptance-time zone
    t0, found, missing = time.time(), {}, []
    for i, s in enumerate(todo):
        cik = mapping.get(norm(s))
        if cik is None:
            missing.append(s)
            continue
        found[s] = cik
        company(cik)
        if (i + 1) % 200 == 0:
            print(json.dumps({"done": i + 1, "of": len(todo), **STATS}), flush=True)
    summary = {"tickers": len(todo), "with_cik": len(found), "no_cik": missing, "seconds": round(time.time() - t0),
               **STATS}
    if args.pilot:
        aapl = json.loads((CACHE / f"{found['AAPL']}.json").read_text())["rows"][-4:] if "AAPL" in found else []
        summary["aapl_last_item_202_filings"] = aapl
    else:
        out = {"user_agent_note": "SEC fair-access UA with the owner's approved contact email",
               "map": found, "no_cik": missing,
               "rows": {s: json.loads((CACHE / f"{c}.json").read_text())["rows"] for s, c in found.items()}}
        (OUT_DIR / "edgar_item_202.json").write_text(json.dumps(out) + "\n")
    print(json.dumps(summary, indent=1), flush=True)


if __name__ == "__main__":
    main()
