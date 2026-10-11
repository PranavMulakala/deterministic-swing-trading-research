"""Data for pre-declared test #33, a $50k weekly wheel on the ten stocks screened as of Dec 31, 2025, run Jan 2 -
Oct 9, 2026 (plan: output/WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md, committed in 073d9e8 before any 2026 option data).

Reuses test #29's data layer (research/wheel_test_v1/data.py) and test #32's EDGAR code (research/wheel_lite_mu_v1/
data.py), both imported and NOT modified, pointed at a SEPARATE folder with its own budget:
- outputs/wheel_ytd_data/ (gitignored). tb3ms.csv is copied once (read-only) from outputs/wheel_lite_mu_data/.
- Databento OPRA.PILLAR cbbo-1m, HARD STOP $15 for this whole test (main + information versions, cumulative across
  runs): every request is priced first with the free metadata.get_cost endpoint, the running total lives in
  outputs/wheel_ytd_data/databento_spent.json, and a request that would pass $15 stops the run. The key is never
  printed.

Earnings sessions (main rule "skip earnings"): test #32's definition, unchanged - SEC EDGAR 8-K filings with Item 2.02
(not 8-K/A), free, User-Agent "Pranav Mulakala pmulakala90@gmail.com"; session = the filing's New York acceptance day
if accepted before 16:00 on a trading day, else the next trading day (lm.earnings_session, called unchanged).
TIME BASE (one deviation from test #32, found while preparing this test): the "...Z" acceptanceDateTime stamps of the
data.sec.gov submissions API are NOT on one time base across companies. Checked against each filing's EDGAR index page
("Accepted", Eastern time) on Oct 11, 2026: Apple, LITE and CVNA files are "shifted" (Eastern time + 4-5 h), while
STX, RKLB, HL and PRAX files are true UTC. Test #32's single Apple-based calibration would therefore put STX/RKLB/HL/
PRAX after-close filings at midday and their sessions one day early. So the acceptance time of every filing that can
matter (filed since 2025-12-01) is read from its index page (cached in edgar/accepted_et.json), converted to true UTC
and passed to lm.earnings_session with shifted=False; each one is checked to equal one of the two readings of the API
stamp (else the run stops), and the results record which reading each filing matched. lm.calibrate (Apple) is still
run and recorded as a cross-check. Two cases the plan did not foresee, handled as documented here:
- AG (First Majestic Silver) is a Canadian foreign private issuer: it files 40-F / 6-K, never 8-K, so it has no Item
  2.02 history. Detected automatically (no 8-K Item 2.02 since 2025-01-01, 6-K/40-F filer). FALLBACK: a 6-K or 6-K/A
  whose news-release exhibit headline says "Financial Results" is that company's Item 2.02 analog. Amendments count
  here because First Majestic's Q4 2025 results were filed only as a 6-K/A (Feb 19, 2026). Conservative: both the
  acceptance-time session (same rule as 8-Ks) and the release date printed in the headline (if a trading day) are
  blocked. Quarterly PRODUCTION releases (also 6-Ks) are recorded and reported but not used (they are operating
  data, not "results of operations and financial condition"). A stock with neither 8-K Item 2.02 nor 6-K filings
  would get no earnings sessions and is flagged in the results (none of the ten is in that case).
- RNA: in 2025 (the screen year) RNA was Avidity Biosciences (CIK 1599901). company_tickers.json now maps RNA to
  Atrium Therapeutics (CIK 2093101), the spin-off that took the RNA symbol on Feb 27, 2026, so the CIK is set by hand
  (EDGAR entity search "Avidity Biosciences" -> 1599901) and the lookup check reports the difference.

Corporate actions (Alpaca, all types, 2025-12-01 .. 2026-10-10, saved to corporate_actions_all_types.json):
- CVNA 5-for-1 forward split, ex May 8, 2026: handled by the engine (open contract closed at mid the day before).
- Regular cash dividends (AG, HL, STX): handled by the engine.
- RNA / Avidity: renamed RNAM on Feb 26, 2026 (its last trading day; its options traded as RNA through Feb 25 and as
  RNAM on Feb 26 only), acquired by Novartis for $72.00 cash per share effective Feb 27, 2026, with 0.1 share of the
  Atrium spin-off (new symbol RNA) per share, ex Feb 27. See DELISTINGS and backtest.py for the treatment. From Feb
  27 the "RNA" price series and option root belong to Atrium, a different company, so they are never used for the
  RNA account except to value the 0.1 spin-off share on Feb 27.
- Anything else (reverse splits, special dividends, other mergers) is flagged by audit_corporate_actions and stops
  the run until it is handled.

  PYTHONPATH=src:. .venv/bin/python -m research.wheel_ytd_v1.data --earnings     # free: EDGAR dates + coverage
  PYTHONPATH=src:. .venv/bin/python -m research.wheel_ytd_v1.data --corporate    # free: Alpaca corporate actions
  PYTHONPATH=src:. .venv/bin/python -m research.wheel_ytd_v1.data --estimate     # free Databento cost estimate
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import html
import json
from pathlib import Path
import random
import re
import statistics
import threading
import time
import urllib.parse
from urllib.request import ProxyHandler, Request, build_opener

from research.wheel_lite_mu_v1 import data as lm
from research.wheel_test_v1 import data as w29

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs/wheel_ytd_data"
TB3MS_FROM = ROOT / "outputs/wheel_lite_mu_data/tb3ms.csv"     # read once, never written
PLAN = "output/WHEEL_YTD_SCREEN_TEST_PLAN_20261011.md"
BUDGET = 15.0
USER_AGENT = lm.USER_AGENT
NY = w29.NY
START, END = date(2026, 1, 2), date(2026, 10, 9)

# The frozen list, exactly as the plan's table: (ticker, name as printed in the plan, Dec 31 2025 price, 2025 return
# %, 60-day volatility %). The order is the plan's (most volatile first).
FROZEN = (
    ("PRAX", "Praxis Precision Medicines", 294.74, 283, 234),
    ("LITE", "Lumentum", 368.59, 339, 97),
    ("RKLB", "Rocket Lab", 69.76, 174, 89),
    ("RIVN", "Rivian", 19.71, 48, 78),
    ("HL", "Hecla Mining", 19.19, 291, 77),
    ("RNA", "Atrium Therapeutics", 72.13, 148, 76),
    ("AG", "First Majestic Silver", 16.66, 204, 75),
    ("COHR", "Coherent", 184.57, 95, 73),
    ("STX", "Seagate", 275.39, 219, 69),
    ("CVNA", "Carvana", 422.02, 108, 68),
)
TICKERS = tuple(r[0] for r in FROZEN)

# SEC CIKs. All from https://www.sec.gov/files/company_tickers.json (fetched Oct 11, 2026) except RNA (see docstring).
CIKS = {"PRAX": 1689548, "LITE": 1633978, "RKLB": 1819994, "RIVN": 1874178, "HL": 719413, "RNA": 1599901,
        "AG": 1308648, "COHR": 820318, "STX": 1137789, "CVNA": 1690820}
CIK_EXCEPTIONS = {"RNA": "company_tickers.json maps RNA to Atrium Therapeutics (CIK 2093101), the Feb 27, 2026 "
                         "spin-off; the 2025/2026-to-Feb-26 RNA stock was Avidity Biosciences (CIK 1599901)"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
RESULTS_SINCE = "2025-01-01"           # lookback used to decide which filing type carries a company's results
ARCHIVES = "https://www.sec.gov/Archives/edgar/data/"
FOREIGN_FORMS = {"6-K", "6-K/A", "40-F", "20-F"}

# RNA (Avidity Biosciences): cash merger + spin-off (Alpaca corporate action ids in "alpaca_ids"; checked against the
# saved file by check_delisting before every run).
DELISTINGS = {
    "RNA": {"company": "Avidity Biosciences", "last_session": date(2026, 2, 25), "effective": date(2026, 2, 27),
            "cash_per_share": 72.0, "acquirer": "NVS", "spinoff_per_share": 0.1, "spinoff_symbol": "RNA",
            "spinoff_company": "Atrium Therapeutics", "renamed_to": "RNAM", "renamed_on": date(2026, 2, 26),
            "alpaca_ids": ["924ad173-9e03-4e63-8067-d57ef37ab24b", "90092415-0851-41ab-a3c8-d1621866a790",
                           "8e1c69a9-37ec-4fc6-975b-b4db8c1d5fbe", "ef20bdb4-1b98-4f34-8f70-904e4ee88109"]},
}
EXTRA_SYMBOLS = ("RNAM",)              # Avidity's symbol on its final day; queried for corporate actions only


# ---------------------------------------------------------------- the frozen list, read back from the plan

def plan_table(path=ROOT / PLAN):
    """[(ticker, name, price, return %, volatility %)] parsed from the plan's frozen-list table."""
    rows = []
    for line in Path(path).read_text().splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*([A-Z]+) \(([^)]*)\)\s*\|\s*\$([\d.,]+)\s*\|\s*\+?(-?\d+)%\s*\|\s*(\d+)%\s*\|",
                     line)
        if m:
            rows.append((m[2], m[3], float(m[4].replace(",", "")), int(m[5]), int(m[6])))
    return tuple(rows)


# ---------------------------------------------------------------- EDGAR (free)

def _edgar_text(url, pause=0.3):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"})
    for attempt in range(6):
        try:
            with build_opener(ProxyHandler({})).open(req, timeout=60) as reply:
                body, enc = reply.read(), reply.headers.get("Content-Encoding", "")
            time.sleep(pause)
            return (gzip.decompress(body) if enc == "gzip" else body).decode("utf-8", "replace")
        except Exception:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))


def check_ciks(company_tickers):
    """{ticker: (ours, company_tickers.json's)} for every disagreement not explained in CIK_EXCEPTIONS, plus the
    explained ones under 'explained'."""
    theirs = {v["ticker"]: int(v["cik_str"]) for v in company_tickers.values()}
    bad, explained = {}, {}
    for t, cik in CIKS.items():
        if theirs.get(t) != cik:
            (explained if t in CIK_EXCEPTIONS else bad)[t] = (cik, theirs.get(t))
    return bad, explained


def fetch_ciks(data=DATA):
    path = data / "edgar" / "company_tickers_subset.json"
    if path.exists():
        return json.loads(path.read_text())
    allt = lm._edgar_json(TICKERS_URL)
    keep = {k: v for k, v in allt.items() if v["ticker"] in TICKERS + EXTRA_SYMBOLS}
    w29._write_json(path, {"source": TICKERS_URL, "fetched_utc": _now(), "rows": keep})
    return {"rows": keep}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


NEEDED_FROM = "2025-12-01"            # filings that can map to a session on or after Jan 2, 2026


def fetch_filings(cik, data=DATA):
    """The company's filings since RESULTS_SINCE from the submissions API (cached; only these fields are saved):
    {'forms': {form: count}, 'rows': [[acceptanceDateTime, filingDate, form, items, accessionNumber], ...]}."""
    path = data / "edgar" / f"{cik}_filings.json"
    if path.exists():
        return json.loads(path.read_text())
    sub = lm._edgar_json(f"{lm.SUBMISSIONS}CIK{cik:010d}.json")
    cols = [sub["filings"]["recent"]]
    if not cols[0]["filingDate"] or min(cols[0]["filingDate"]) > RESULTS_SINCE:
        cols += [lm._edgar_json(lm.SUBMISSIONS + f["name"]) for f in sub["filings"].get("files", [])
                 if f.get("filingTo", "9999") >= RESULTS_SINCE]
    rows = sorted([acc, filed, form, items or "", num] for c in cols
                  for form, items, acc, filed, num in zip(c["form"], c["items"], c["acceptanceDateTime"],
                                                          c["filingDate"], c["accessionNumber"])
                  if filed >= RESULTS_SINCE)
    forms = {}
    for r in rows:
        forms[r[2]] = forms.get(r[2], 0) + 1
    out = {"cik": cik, "name": sub.get("name"), "since": RESULTS_SINCE, "forms": forms, "rows": rows,
           "user_agent": USER_AGENT, "fetched_utc": _now()}
    w29._write_json(path, out)
    return out


def item202_rows(filings):
    """[[acceptanceDateTime, filingDate, items, accession]]: form == '8-K' and '2.02' among the items (test #16/#32's
    research/ep_test_v1/fetch_edgar.earnings_rows rule, plus the accession number)."""
    return [[r[0], r[1], r[3], r[4]] for r in filings["rows"]
            if r[2] == "8-K" and "2.02" in [i.strip() for i in r[3].split(",")]]


_accepted_lock = threading.Lock()


def fetch_accepted(cik, accession, data=DATA):
    """The 'Accepted' time on the filing's EDGAR index page, Eastern time 'YYYY-MM-DD HH:MM:SS' (cached)."""
    path = data / "edgar" / "accepted_et.json"
    with _accepted_lock:
        cache = json.loads(path.read_text()) if path.exists() else {}
        if accession in cache:
            return cache[accession]
    page = _edgar_text(f"{ARCHIVES}{cik}/{accession.replace('-', '')}/{accession}-index.htm")
    m = re.search(r'Accepted</div>\s*<div class="info">\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*<', page)
    if not m:
        raise RuntimeError(f"no Accepted time on the index page of {accession}")
    with _accepted_lock:
        cache = json.loads(path.read_text()) if path.exists() else {}
        cache[accession] = m[1]
        w29._write_json(path, dict(sorted(cache.items())))
    return m[1]


def et_to_utc_stamp(et):
    """'2026-07-28 16:07:21' (New York) -> '2026-07-28T20:07:21.000Z' (true UTC)."""
    t = datetime.strptime(et, "%Y-%m-%d %H:%M:%S").replace(tzinfo=NY).astimezone(timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def reading_of(stamp, et):
    """Which reading of the API stamp gives the index page's Eastern time: 'utc', 'shifted', or raises."""
    want = datetime.strptime(et, "%Y-%m-%d %H:%M:%S")
    for name, shifted in (("utc", False), ("shifted", True)):
        if lm.acceptance_ny(stamp, shifted).replace(tzinfo=None) == want:
            return name
    raise RuntimeError(f"API stamp {stamp} matches neither reading of the index page time {et}")


def earnings_source(item202, forms):
    """'8-K Item 2.02' if the company filed any since RESULTS_SINCE; '6-K financial results (fallback)' for a
    foreign private issuer; else 'none' (earnings skipping cannot be applied; reported)."""
    if any(r[1] >= RESULTS_SINCE for r in item202):
        return "8-K Item 2.02"
    if FOREIGN_FORMS & set(forms):
        return "6-K financial results (fallback)"
    return "none"


MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def classify_headline(headline):
    if re.search(r"financial\s+results", headline, re.I):
        return "financial_results"
    if re.search(r"production\s+results|\bproduces\b.*\b(ounces|oz)\b|\bproduction and 20\d\d outlook", headline,
                 re.I):
        return "production_results"
    return "other"


def release_date(headline):
    m = re.search(rf"({MONTHS})\s+(\d{{1,2}}),\s+(\d{{4}})", headline)
    return datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%B %d %Y").date().isoformat() if m else None


def _strip(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def pick_exhibit(names):
    """The news-release exhibit of a 6-K: a '*financialnr*' document if any, else the first EX-99 style document."""
    htm = sorted(n for n in names if n.lower().endswith(".htm"))
    fin = [n for n in htm if "financialnr" in n.lower()]
    ex = [n for n in htm if re.search(r"(ex|exhibit|dex)[-_]?99", n, re.I)]
    return (fin or ex or [None])[0]


def fetch_6k(cik, filings, data=DATA):
    """Every 6-K / 6-K/A since RESULTS_SINCE with its news-release headline and category (cached; only these
    extracted rows are saved). Row: {acceptance, filing_date, form, accession, exhibit, headline, release_date,
    category}."""
    path = data / "edgar" / f"{cik}_6k.json"
    if path.exists():
        return json.loads(path.read_text())["rows"]
    rows = []
    for stamp, filed, form, _, acc in filings["rows"]:
        if form not in ("6-K", "6-K/A"):
            continue
        folder = f"{ARCHIVES}{cik}/{acc.replace('-', '')}/"
        names = [d["name"] for d in lm._edgar_json(folder + "index.json")["directory"]["item"]]
        ex = pick_exhibit(names)
        head = _strip(_edgar_text(folder + ex))[:400] if ex else ""
        rows.append({"acceptance": stamp, "filing_date": filed, "form": form, "accession": acc, "exhibit": ex,
                     "headline": head, "release_date": release_date(head), "category": classify_headline(head)})
    rows.sort(key=lambda r: r["acceptance"])
    w29._write_json(path, {"cik": cik, "since": RESULTS_SINCE, "user_agent": USER_AGENT, "rows": rows,
                           "fetched_utc": _now()})
    return rows


def timed(cik, rows, data=DATA):
    """Adds the index-page Eastern acceptance time, the true-UTC stamp and the matching API reading to each row
    (dicts with 'acceptance' and 'accession') filed since NEEDED_FROM; earlier rows are dropped."""
    out = []
    for r in rows:
        if r["filing_date"] < NEEDED_FROM:
            continue
        et = fetch_accepted(cik, r["accession"], data)
        out.append({**r, "accepted_et": et, "acceptance_utc": et_to_utc_stamp(et),
                    "api_stamp_reading": reading_of(r["acceptance"], et)})
    return out


def sessions_from(rows, trading_days):
    """Test #32's session rule on the true-UTC acceptance times."""
    return lm.earnings_sessions([[r["acceptance_utc"]] for r in rows], list(trading_days), shifted=False)


def fallback_sessions(rows, trading_days):
    """Sessions for 6-K financial-results rows: the acceptance-time session (test #32's rule) AND the headline's
    release date (that day if it is a trading day, else the next one), both blocked. Dropped if before the window."""
    days = list(trading_days)
    out = set()
    for r in rows:
        if r["category"] != "financial_results":
            continue
        s = lm.earnings_session(r["acceptance_utc"], days, shifted=False)
        if s is not None:
            out.add(s)
        if r.get("release_date"):
            rd = date.fromisoformat(r["release_date"])
            if rd >= days[0]:
                later = [d for d in days if d >= rd]
                out.add(later[0] if later else rd)
    return sorted(out)


def earnings(days, data=DATA, tickers=TICKERS):
    """({ticker: [sessions]}, {ticker: coverage}, Apple calibration as a cross-check). days: the test's days."""
    cal = lm.calibrate(data)
    sessions, coverage = {}, {}
    for t in tickers:
        cik = CIKS[t]
        filings = fetch_filings(cik, data)
        rows = item202_rows(filings)
        src = earnings_source(rows, filings["forms"])
        last = account_last_day(t, days)
        info = {"cik": cik, "company": filings.get("name"), "source": src, "forms_since_2025": filings["forms"],
                "item202_filings_since_2025": len(rows)}
        if src == "8-K Item 2.02":
            used = timed(cik, [{"acceptance": r[0], "filing_date": r[1], "items": r[2], "accession": r[3]}
                               for r in rows], data)
            s = sessions_from(used, days)
            info["filings_used"] = used
        elif src.startswith("6-K"):
            six = fetch_6k(cik, filings, data)
            used = timed(cik, [r for r in six if r["category"] == "financial_results"], data)
            prod = timed(cik, [r for r in six if r["category"] == "production_results"], data)
            s = fallback_sessions(used, days)
            info.update({"filings_used": used, "production_releases_not_used": prod,
                         "production_release_sessions_not_used": fallback_sessions(
                             [{**r, "category": "financial_results"} for r in prod], days)})
        else:
            s, used = [], []
            info["flag"] = "no 8-K Item 2.02 and no 6-K filings: earnings skipping cannot be applied to this stock"
        # what test #32's single Apple-based reading would have given, for the record
        apple = sorted({x for r in used if (x := lm.earnings_session(r["acceptance"], list(days), cal["shifted"]))})
        info["sessions_with_test32_apple_reading"] = [d.isoformat() for d in apple if days[0] <= d <= last]
        sessions[t] = s
        info["sessions_in_wheel_window"] = [d.isoformat() for d in s if days[0] <= d <= last]
        info["wheel_window_last_session"] = last.isoformat()
        coverage[t] = info
    return sessions, coverage, cal


# ---------------------------------------------------------------- corporate actions (Alpaca, free)

def fetch_all_corporate_actions(data=DATA, symbols=TICKERS + EXTRA_SYMBOLS):
    path = data / "corporate_actions_all_types.json"
    if path.exists():
        return json.loads(path.read_text())
    out, token = {}, None
    while True:
        q = {"symbols": ",".join(symbols), "start": "2025-12-01", "end": (END + timedelta(days=1)).isoformat(),
             "limit": 1000}
        if token:
            q["page_token"] = token
        page = w29.alpaca(f"/v1/corporate-actions?{urllib.parse.urlencode(q)}")
        for k, v in (page.get("corporate_actions") or {}).items():
            out.setdefault(k, []).extend(v)
        token = page.get("next_page_token")
        if not token:
            break
    w29._write_json(path, out)
    return out


def _action_day(x):
    return x.get("ex_date") or x.get("effective_date") or x.get("process_date")


def _action_symbol(x):
    return x.get("symbol") or x.get("acquiree_symbol") or x.get("source_symbol") or x.get("old_symbol")


def audit_corporate_actions(ca, first=START, last=END, delistings=DELISTINGS):
    """Sorts every action dated inside the window into handled_by_engine (forward splits, regular cash dividends),
    handled_here (the documented delistings) and flagged (anything else: must be handled before a run)."""
    ids = {i for cfg in delistings.values() for i in cfg["alpaca_ids"]}
    out = {"handled_by_engine": [], "handled_here": [], "flagged": [], "outside_window": 0}
    for kind, items in sorted(ca.items()):
        for x in items:
            day = _action_day(x)
            if not day or not first.isoformat() <= day <= last.isoformat():
                out["outside_window"] += 1
                continue
            row = {"type": kind, "symbol": _action_symbol(x), "day": day, "id": x.get("id"), "detail": x}
            if kind == "forward_splits" or (kind == "cash_dividends" and not x.get("special")):
                out["handled_by_engine"].append(row)
            elif x.get("id") in ids:
                out["handled_here"].append(row)
            else:
                out["flagged"].append(row)
    return out


def check_delisting(ca, ticker="RNA", cfg=None):
    """Raises if the saved Alpaca corporate actions disagree with DELISTINGS[ticker]."""
    cfg = cfg or DELISTINGS[ticker]
    eff = cfg["effective"].isoformat()
    merger = [x for x in ca.get("cash_mergers", []) if x.get("acquiree_symbol") == cfg["renamed_to"]]
    spin = [x for x in ca.get("spin_offs", []) if x.get("source_symbol") == cfg["renamed_to"]]
    rename = [x for x in ca.get("name_changes", []) if x.get("old_symbol") == ticker]
    problems = []
    if not merger or any(x.get("effective_date") != eff or float(x.get("rate")) != cfg["cash_per_share"]
                         for x in merger):
        problems.append(f"cash merger: {merger}")
    if len(spin) != 1 or spin[0].get("ex_date") != eff or spin[0].get("new_symbol") != cfg["spinoff_symbol"] or \
            abs(float(spin[0]["new_rate"]) / float(spin[0]["source_rate"]) - cfg["spinoff_per_share"]) > 1e-12:
        problems.append(f"spin-off: {spin}")
    if len(rename) != 1 or rename[0].get("new_symbol") != cfg["renamed_to"] or \
            rename[0].get("process_date") != cfg["renamed_on"].isoformat():
        problems.append(f"name change: {rename}")
    found = {x.get("id") for x in merger + spin + rename}
    if not set(cfg["alpaca_ids"]) <= found:
        problems.append(f"ids {sorted(set(cfg['alpaca_ids']) - found)} not found")
    if problems:
        raise RuntimeError(f"{ticker} delisting config disagrees with Alpaca: " + "; ".join(problems))
    return True


# ---------------------------------------------------------------- provider (test #29's, separate folder + budget)

def make_provider(data=DATA, budget=BUDGET, db=None):
    lm.ensure_tbill_file(data, TB3MS_FROM)
    return w29.Provider(tickers=TICKERS, data=data, db=db, budget=budget)


def fetch_spot_before(ticker, day, data=DATA):
    """Holding-entry fallback when a stock has no 15:45 SIP 1-minute bar on the first day (PRAX on Jan 2, 2026):
    the close of the last 1-minute bar from 15:30 up to (not including) 15:45, i.e. the price prevailing at 15:45.
    Returns {'price', 'bar_start_utc'} (cached), or raises if there is none."""
    path = data / "spot1545_fallback" / f"{day.isoformat()}_{ticker}.json"
    if path.exists():
        return json.loads(path.read_text())
    start, cut = datetime.combine(day, w29.dtime(15, 30), NY), datetime.combine(day, w29.DECIDE, NY)
    q = {"timeframe": "1Min", "feed": "sip", "adjustment": "raw", "limit": 100,
         "start": w29._utc(start), "end": w29._utc(cut - timedelta(seconds=1))}
    bars = [b for b in w29.alpaca(f"/v2/stocks/{ticker}/bars?{urllib.parse.urlencode(q)}").get("bars") or []
            if b["t"] < w29._utc(cut)]
    if not bars:
        raise RuntimeError(f"{ticker}: no 1-minute bar 15:30-15:45 on {day}")
    out = {"price": bars[-1]["c"], "bar_start_utc": bars[-1]["t"], "rule": "close of the last 1-minute bar before 15:45"}
    w29._write_json(path, out)
    return out


def window_days(provider):
    return provider.trading_days(START, END)


def account_last_day(ticker, days):
    """The last trading day the account can wheel its stock (the day before a delisting's rename, else the end)."""
    cfg = DELISTINGS.get(ticker)
    return min(days[-1], cfg["last_session"]) if cfg else days[-1]


# ---------------------------------------------------------------- free dry-run cost estimate

def estimate(samples_per_ticker=8, seed=33):
    """Prices sample 15:45 chain minutes (spread over each account's 2026 window) and ~1-2 week contract windows for
    every stock with the free metadata.get_cost endpoint. Buys nothing; the spent file is not touched."""
    db = w29.Databento(BUDGET, DATA)
    prov = make_provider(db=db)
    days = window_days(prov)
    rng = random.Random(seed)
    out = {"chain_minute": {}, "contract_window": {}, "sample_days": {}, "window_trading_days": {}}
    for t in TICKERS:
        last = account_last_day(t, days)
        mine = [d for d in days if d <= last]
        k = min(samples_per_ticker, len(mine))
        step = len(mine) / k
        picks = sorted({mine[min(len(mine) - 1, int(i * step + rng.random() * step))] for i in range(k)})
        chain_costs, window_costs = [], []
        for d in picks:
            start = datetime.combine(d, w29.DECIDE, NY)
            chain_costs.append(db.cost(f"{t}.OPT", "parent", start, datetime.combine(d, w29.DECIDE_END, NY)))
            spot = prov.close(t, d)
            fri = d + timedelta(days=(4 - d.weekday()) % 7 + 7)
            step_k = 5 if spot > 200 else (2.5 if spot > 50 else (1 if spot > 10 else 0.5))
            strike = round(0.95 * spot / step_k) * step_k
            end = max(x for x in mine if x <= fri) if fri <= mine[-1] else mine[-1]
            try:
                for root, a, b in w29.quote_segments(t, d, end):
                    window_costs.append(db.cost(w29.osi(root, fri, "P", strike), "raw_symbol", a, b))
            except RuntimeError as e:
                window_costs.append(None)
                print(json.dumps({"window_cost_error": str(e)[:160], "ticker": t, "day": d.isoformat(),
                                  "strike": strike, "expiration": fri.isoformat()}))
        out["sample_days"][t] = [d.isoformat() for d in picks]
        out["chain_minute"][t] = [round(c, 6) for c in chain_costs]
        out["contract_window"][t] = [None if c is None else round(c, 6) for c in window_costs]
        out["window_trading_days"][t] = len(mine)
    out["projection"] = project(out)
    return out, len(days), db.spent


def project(est, chain_share_expected=0.75, contracts_per_week_expected=1.5, contracts_per_week_upper=3.0,
            versions=4):
    """Dollar projection. Chains are cached per stock and day, so all versions share them: expected = 75% of the
    window's days (test #32 fetched a 2026 chain on ~70% of days), upper = every day. Contract windows: expected
    1.5 a week per version (50% buybacks resell), upper 3 a week, times 4 versions with no sharing."""
    per, total_exp, total_up = {}, 0.0, 0.0
    for t, chains in est["chain_minute"].items():
        n = est["window_trading_days"][t]
        weeks = n / 5
        c = statistics.mean(chains)
        w = [x for x in est["contract_window"][t] if x is not None]
        wmean = statistics.mean(w) if w else 0.001
        exp = chain_share_expected * n * c + versions * contracts_per_week_expected * weeks * wmean * 0.6
        up = n * max(chains) + versions * contracts_per_week_upper * weeks * max(w or [0.001])
        per[t] = {"mean_chain": round(c, 6), "max_chain": round(max(chains), 6), "mean_window": round(wmean, 6),
                  "expected": round(exp, 3), "upper": round(up, 3)}
        total_exp += exp
        total_up += up
    return {"per_stock": per, "expected_total": round(total_exp, 2), "upper_total": round(total_up, 2),
            "note": "expected assumes ~40% of contract windows are shared between versions (same day, same pick)"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--estimate", action="store_true", help="free Databento cost estimate (no purchase)")
    ap.add_argument("--earnings", action="store_true", help="fetch (free) and print the EDGAR earnings sessions")
    ap.add_argument("--corporate", action="store_true", help="fetch (free) and audit Alpaca corporate actions")
    args = ap.parse_args()
    if args.corporate:
        ca = fetch_all_corporate_actions()
        check_delisting(ca)
        aud = audit_corporate_actions(ca)
        print(json.dumps({k: (v if k == "outside_window" else [{x: r[x] for x in ("type", "symbol", "day")}
                                                                for r in v]) for k, v in aud.items()}, indent=1))
    if args.earnings:
        bad, explained = check_ciks(fetch_ciks()["rows"])
        print(json.dumps({"cik_mismatches": bad, "cik_explained": explained}))
        prov = make_provider()
        days = window_days(prov)
        sessions, coverage, cal = earnings(days)
        print(json.dumps({"calibration": cal}))
        for t in TICKERS:
            c = coverage[t]
            print(json.dumps({"ticker": t, "source": c["source"], "sessions": c["sessions_in_wheel_window"],
                              "with_test32_apple_reading": c["sessions_with_test32_apple_reading"],
                              "filings": [[r["accepted_et"], r["api_stamp_reading"], r["form"] if "form" in r
                                           else r.get("items")] for r in c.get("filings_used", [])],
                              "production_sessions_not_used": [d.isoformat() for d in
                                                               c.get("production_release_sessions_not_used", [])],
                              "flag": c.get("flag")}))
    if args.estimate:
        out, n_days, spent = estimate()
        print(json.dumps({"trading_days": n_days, "spent_so_far_in_this_tests_budget": spent, **out}, indent=1))


if __name__ == "__main__":
    main()
