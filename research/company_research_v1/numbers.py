"""Company research helper (pillar 3 of the Oct 7, 2026 plan): the conviction checklist's "proof in the numbers" and
"price check" steps (output/COMPANY_CONVICTION_CHECKLIST.md), from primary data. Read-only; research, not advice.

  PYTHONPATH=src:. .venv/bin/python -m research.company_research_v1.numbers MU

Quarterly revenue, growth vs a year earlier and gross margin come from the company's own SEC filings (XBRL
companyconcept, 10-Q and 10-K; a fiscal Q4 is the year minus its three quarters). A quarter that so far is only in an
earnings press release (8-K) shows up once its 10-Q/10-K is filed. Prices are Alpaca SIP daily closes, split-adjusted.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import urllib.parse

CONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{name}.json"
REVENUE = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
           "RevenueFromContractWithCustomerIncludingAssessedTax")
COST = ("CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold")
FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A"}


def days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def quarters(facts):
    """{quarter end: value} from a companyconcept USD list: 3-month periods as filed (the latest filing wins), plus each
    fiscal Q4 derived as the year minus the three quarters inside it. Year-to-date (6- and 9-month) values are skipped."""
    latest = {}
    for r in facts:
        if r.get("form") in FORMS and r.get("start"):
            key = (r["start"], r["end"])
            if key not in latest or r["filed"] > latest[key]["filed"]:
                latest[key] = r
    three = {k: r["val"] for k, r in latest.items() if 80 <= days(*k) <= 100}
    out = {e: v for (_, e), v in three.items()}
    for (s, e), r in latest.items():
        if 350 <= days(s, e) <= 380 and e not in out:
            inside = [v for (qs, qe), v in three.items() if qs >= s and qe < e]
            if len(inside) == 3:
                out[e] = r["val"] - sum(inside)
    return dict(sorted(out.items()))


def growth(q):
    """[(end, value, change vs the quarter ending 51-53 weeks earlier, or None)]."""
    ends = sorted(q)
    rows = []
    for e in ends:
        prev = next((p for p in ends if 357 <= days(p, e) <= 371), None)
        rows.append((e, q[e], q[e] / q[prev] - 1 if prev and q[prev] else None))
    return rows


def price_check(series):
    """Price facts from [(date, close)]: last close, this year so far, the past year's high and low, and the past
    year's worst drop from a high (closing prices)."""
    last_d, last = series[-1]
    year_ago = (date.fromisoformat(last_d) - timedelta(days=365)).isoformat()
    window = [(d, c) for d, c in series if d >= year_ago]
    before_year = [c for d, c in series if d < last_d[:4] + "-01-01"]
    peak_d, peak = window[0]
    worst = (0.0, None, None, None, None)
    for d, c in window:
        if c > peak:
            peak_d, peak = d, c
        if c / peak - 1 < worst[0]:
            worst = (c / peak - 1, peak_d, peak, d, c)
    hi, lo = max(window, key=lambda x: x[1]), min(window, key=lambda x: x[1])
    return {"last": (last_d, last), "year_start": before_year[-1] if before_year else None,
            "this_year_pct": round(100 * (last / before_year[-1] - 1), 1) if before_year else None,
            "one_year_high": hi, "one_year_low": lo, "below_high_pct": round(100 * (last / hi[1] - 1), 1),
            "worst_drop_pct": round(100 * worst[0], 1), "worst_drop": worst[1:]}


def sec_numbers(ticker):
    from research.ep_test_v1.fetch_edgar import TICKERS_URL, get_json
    cik = next(int(r["cik_str"]) for r in get_json(TICKERS_URL).values() if r["ticker"] == ticker.upper())

    def concept(names):
        for name in names:
            page = get_json(CONCEPT.format(cik=cik, name=name))
            if page and page.get("units", {}).get("USD"):
                q = quarters(page["units"]["USD"])
                if q:
                    return name, q
        return None, {}

    rev_name, rev = concept(REVENUE)
    gp_name, gp = concept(("GrossProfit",))
    if not gp:
        gp_name, cost = concept(COST)
        gp = {e: rev[e] - c for e, c in cost.items() if e in rev}
    return {"cik": cik, "revenue_concept": rev_name, "gross_concept": gp_name,
            "quarters": [{"end": e, "revenue": v, "vs_year_earlier_pct": round(100 * g, 1) if g is not None else None,
                          "gross_margin_pct": round(100 * gp[e] / v, 1) if e in gp and v else None}
                         for e, v, g in growth(rev)]}


def closes(symbol, first):
    from research.forward_watch_v1.watch import get
    from research.lite_dip_history_v1.run import DATA
    end = (datetime.now(timezone.utc) - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, token = [], None
    while True:
        q = {"timeframe": "1Day", "feed": "sip", "adjustment": "split", "limit": 10000,
             "start": f"{first}T00:00:00Z", "end": end}
        if token:
            q["page_token"] = token
        page = get(f"{DATA}/v2/stocks/{symbol}/bars?{urllib.parse.urlencode(q)}")
        out += [(r["t"][:10], r["c"]) for r in page.get("bars") or []]
        token = page.get("next_page_token")
        if not token:
            return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument("--quarters", type=int, default=8)
    args = parser.parse_args()
    sec = sec_numbers(args.ticker)
    series = closes(args.ticker.upper(), (date.today() - timedelta(days=800)).isoformat())
    print(f"{args.ticker.upper()} (SEC CIK {sec['cik']}; revenue: {sec['revenue_concept']}; gross: {sec['gross_concept']})")
    for r in sec["quarters"][-args.quarters:]:
        g = f"{r['vs_year_earlier_pct']:+.0f}%" if r["vs_year_earlier_pct"] is not None else "n/a"
        m = f"{r['gross_margin_pct']:.1f}%" if r["gross_margin_pct"] is not None else "n/a"
        print(f"  quarter ending {r['end']}: revenue ${r['revenue'] / 1e9:,.2f}B  vs a year earlier {g:>6}  gross margin {m}")
    print(json.dumps(price_check(series), indent=1))


if __name__ == "__main__":
    main()
