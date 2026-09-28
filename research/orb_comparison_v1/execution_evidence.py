"""Read-only follow-up for all observed replay gaps and primary entry windows."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time

from swingbot.alpaca_paper import AlpacaPaperClient
from swingbot.paper_cli import _load_env
from research.lite_execution_data.quotes import nanos, quote_at
from .collect import ROOT, SYMBOLS, save, digest


class EvidenceClient(AlpacaPaperClient):
    def _request(self, method, path, *, data_api=False, query=None, **kwargs):
        allowed = {f"/v2/stocks/{s}/{kind}" for s in SYMBOLS for kind in ("bars", "trades", "quotes")}
        if method != "GET" or not data_api or path not in allowed or kwargs:
            raise ValueError("Only scoped historical data GETs permitted")
        return super()._request(method, path, data_api=True, query=query)


def window(client, symbol, kind, start, end, pause=time.sleep):
    query = {"feed": "sip", "start": start.isoformat(), "end": end.isoformat(), "limit": 10000, "sort": "asc"}
    if kind == "bars": query.update(timeframe="1Min", adjustment="raw", asof="2026-09-04")
    path = f"/v2/stocks/{symbol}/{kind}"
    rows, seen, token = [], set(), None
    for page in range(1, 6):
        pause(.35)
        response = client._request("GET", path, data_api=True, query={**query, **({"page_token":token} if token else {})})
        if not isinstance(response,dict) or response.get("symbol") != symbol or kind not in response:
            raise ValueError("Invalid historical response")
        chunk=response[kind]
        # Alpaca explicitly returns bars:null for an empty terminal window.
        # A missing key or a null nonterminal page is not an empty success.
        null_terminal=chunk is None and response.get("next_page_token") is None
        if null_terminal: chunk=[]
        if not isinstance(chunk,list): raise ValueError("Invalid historical rows")
        left,right=nanos(start.isoformat()),nanos(end.isoformat())
        if any(not left <= nanos(r["t"]) <= right for r in chunk):
            raise ValueError("Historical observation outside requested window")
        rows.extend(chunk)
        token=response.get("next_page_token")
        if token is None:
            return {"complete":True,"path":path,"query":query,"rows":rows,"pages":page,"terminal_collection_was_null":null_terminal}
        if not isinstance(token,str) or not token or token in seen: raise ValueError("Stalled pagination")
        seen.add(token)
    return {"complete":False,"path":path,"query":query,"rows":rows,"pages":5}


def plan(results):
    gaps, entries = set(), set()
    for name,result in results.items():
        if result["unresolved"]:
            gaps.update((s,result["unresolved"]["time"]) for s in result["unresolved"]["symbols"])
        if name.startswith("primary_"):
            entries.update((event["symbol"],event["time"]) for event in result["events"] if event["type"]=="entry")
    return sorted(gaps),sorted(entries)


def analyze(payload, results):
    gaps=[]
    for item in payload["gaps"]:
        bars,trades=item["bars"],item["trades"]
        gaps.append({"symbol":item["symbol"],"time":item["time"],"bar_recheck_complete":bars["complete"],
                     "bars_returned":len(bars["rows"]),"trade_query_complete":trades["complete"],
                     "trades_returned":len(trades["rows"]),
                     "trade_condition_counts":dict(Counter(",".join(r.get("c",[])) for r in trades["rows"]))})
    entries=[]
    for item in payload["entries"]:
        readings={}
        for label,delay in (("100ms",100000000),("1s",1000000000),("2s",2000000000)):
            reading=quote_at(item["quotes"]["rows"],nanos(item["time"])+delay,1e100) if item["quotes"]["complete"] else {"status":"UNKNOWN_TRUNCATED"}
            reading.pop("ask_within_raw_limit",None)
            readings[label]=reading
        related=[]
        for name,result in results.items():
            if not name.startswith("primary_"): continue
            for event in result["events"]:
                if event["type"]=="entry" and (event["symbol"],event["time"])==(item["symbol"],item["time"]):
                    observed=readings["1s"]
                    related.append({"run":name,"modeled_entry":event["entry"],"quantity":event["qty"],
                                    "ask_above_modeled_entry_at_1s": observed["ask"]>float(event["entry"]) if observed["status"]=="OBSERVED" else None})
        entries.append({"symbol":item["symbol"],"time":item["time"],"readings":readings,"runs":related})
    observed=[i["readings"]["1s"] for i in entries if i["readings"]["1s"]["status"]=="OBSERVED"]
    return {"gaps":gaps,"entries":entries,"entry_windows":len(entries),"observed_at_1s":len(observed),
            "spread_over_15bps_at_1s":sum(r["full_spread_bps"]>15 for r in observed),
            "status":"diagnostic_quotes_not_fills_not_original_bar_receipt", "does_not_modify_frozen_data":True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    results=json.loads(args.results.read_text())
    gaps,entries=plan(results)
    args.output.mkdir(parents=True,exist_ok=False)
    _load_env(ROOT/".env")
    client=EvidenceClient(os.environ.get("ALPACA_PAPER_API_KEY",""),os.environ.get("ALPACA_PAPER_API_SECRET",""))
    payload={"results_sha256":digest(args.results),"collector_sha256":digest(__file__),"gaps":[],"entries":[]}
    try:
        for symbol,t in gaps:
            start=datetime.fromisoformat(t)
            end=start+timedelta(minutes=1,microseconds=-1)
            payload["gaps"].append({"symbol":symbol,"time":t,
                                    "bars":window(client,symbol,"bars",start,end),"trades":window(client,symbol,"trades",start,end)})
            print(f"Rechecked {symbol} {t}",flush=True)
        for symbol,t in entries:
            stamp=datetime.fromisoformat(t)
            payload["entries"].append({"symbol":symbol,"time":t,"quotes":window(client,symbol,"quotes",stamp-timedelta(seconds=2),stamp+timedelta(seconds=2))})
        payload["completed_at"]=datetime.now(timezone.utc).isoformat()
        evidence=save(args.output/"raw.json",payload)
        report=analyze(payload,results)
        report["raw_evidence"]=evidence
        save(args.output/"report.json",report)
        print(json.dumps({k:v for k,v in report.items() if k!="entries"},indent=2))
    except Exception as exc:
        save(args.output/"incomplete.json",{"error_type":type(exc).__name__,"payload":payload})
        print(json.dumps({"complete":False,"error_type":type(exc).__name__,"provider_body":"suppressed"}))
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
