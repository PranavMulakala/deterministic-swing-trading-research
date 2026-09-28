"""Bounded, GET-only Alpaca historical-data/account checks. Never sends orders.

PYTHONPATH=src .venv/bin/python -m research.lite_execution_data.collect probe --output NEW_DIR
Other commands: bars (raw SIP 1Min and 5Min), quotes (bounded timestamp windows).
Existing files/directories are never overwritten. Credentials are loaded locally,
never printed or persisted. Only paper account and official market-data hosts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from swingbot.alpaca_paper import AlpacaPaperClient, AlpacaPaperError
from swingbot.paper_cli import _load_env

ROOT = Path(__file__).resolve().parents[2]
PAPER_PATHS = {"/v2/account", "/v2/account/configurations", "/v2/assets/LITE",
               "/v2/positions", "/v2/orders", "/v2/clock", "/v2/calendar"}
DATA_PATHS = {f"/v2/stocks/{s}/{kind}" for s in ("LITE", "SPY") for kind in ("bars", "quotes", "trades")}


class ReadOnlyClient(AlpacaPaperClient):
    def _request(self, method, path, *, data_api=False, query=None, **kwargs):
        if method != "GET" or kwargs or path not in (DATA_PATHS if data_api else PAPER_PATHS):
            raise ValueError("Research collector permits only allowlisted GET requests")
        return super()._request("GET", path, data_api=data_api, query=query)


def new_client():
    _load_env(ROOT / ".env")
    return ReadOnlyClient(os.environ.get("ALPACA_PAPER_API_KEY", ""),
                          os.environ.get("ALPACA_PAPER_API_SECRET", ""), timeout=20)


def save(path: Path, payload):
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)+"\n").encode()
    with path.open("xb") as handle:
        handle.write(raw)
    return {"file":path.name, "sha256":hashlib.sha256(raw).hexdigest(), "bytes":len(raw)}


def paged(client, path, query, field, max_pages=30):
    rows, token, seen = [], None, set()
    for page in range(max_pages):
        reply = client._request("GET", path, data_api=True,
                                query={**query, **({"page_token":token} if token else {})})
        chunk = reply.get(field)
        if not isinstance(chunk, list):
            raise ValueError("Unexpected historical response shape")
        if reply.get("symbol") != path.split("/")[3]:
            raise ValueError("Unexpected historical symbol")
        rows.extend(chunk)
        token = reply.get("next_page_token")
        if not token:
            return {"rows":rows, "pages":page+1, "complete":True, "query":query, "path":path}
        if not isinstance(token, str) or token in seen or not chunk:
            raise ValueError("Stalled historical pagination")
        seen.add(token)
    # Never label a truncated response complete or silently discard its boundary.
    return {"rows":rows, "pages":max_pages, "complete":False,
            "reason":"page_budget_exhausted", "query":query, "path":path}


def probe(client):
    result = {"observed_at":datetime.now(timezone.utc).isoformat(), "paper_only":True,
              "orders_sent":0, "checks":{}}
    requests = [
        ("account", "/v2/account", False, None),
        ("asset", "/v2/assets/LITE", False, None),
        ("account_configuration", "/v2/account/configurations", False, None),
        ("positions", "/v2/positions", False, None),
        ("open_orders", "/v2/orders", False, {"status":"open", "limit":500, "nested":"true"}),
        ("clock", "/v2/clock", False, None),
        ("sip_minute_sample", "/v2/stocks/LITE/bars", True,
         {"feed":"sip", "timeframe":"1Min", "adjustment":"raw", "start":"2026-01-02T14:30:00Z", "end":"2026-01-02T14:40:00Z", "limit":100}),
        ("sip_quote_sample", "/v2/stocks/LITE/quotes", True,
         {"feed":"sip", "start":"2026-09-04T14:00:00Z", "end":"2026-09-04T14:00:01Z", "limit":10}),
        ("sip_trade_sample", "/v2/stocks/LITE/trades", True,
         {"feed":"sip", "start":"2026-09-04T14:00:00Z", "end":"2026-09-04T14:00:01Z", "limit":10}),
    ]
    allow = {
        "account":("status", "currency", "cash", "equity", "buying_power", "non_marginable_buying_power",
                   "multiplier", "pattern_day_trader", "daytrade_count", "trading_blocked", "account_blocked",
                   "trade_suspended_by_user", "long_market_value", "short_market_value", "initial_margin", "maintenance_margin"),
        "asset":("symbol", "class", "exchange", "status", "tradable", "fractionable", "marginable", "attributes"),
        "account_configuration":("fractional_trading", "dtbp_check", "trade_confirm_email", "suspend_trade", "no_shorting", "max_margin_multiplier", "pdt_check"),
        "clock":("timestamp", "is_open", "next_open", "next_close"),
    }
    for name, path, data_api, query in requests:
        try:
            response = client._request("GET", path, data_api=data_api, query=query)
            if name in allow:
                clean = {k:response.get(k) for k in allow[name]}
            elif name in ("positions", "open_orders"):
                if not isinstance(response, list):
                    raise ValueError("Expected a list")
                clean = {"count":len(response), "possibly_truncated":name == "open_orders" and len(response) == 500}
            else:
                field = {"sip_minute_sample":"bars", "sip_quote_sample":"quotes", "sip_trade_sample":"trades"}[name]
                clean = {"query":query, "records":response.get(field), "symbol":response.get("symbol"),
                         "more_available":bool(response.get("next_page_token"))}
            result["checks"][name] = {"status":"READ_OK", "data":clean}
        except (AlpacaPaperError, ValueError, TypeError, KeyError) as exc:
            result["checks"][name] = {"status":"UNAVAILABLE", "error":str(exc)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("probe", "bars", "quotes"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--windows", type=Path, help="JSON list of declared quote windows")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Output exists; use a fresh directory")
    windows = json.loads(args.windows.read_text()) if args.command == "quotes" and args.windows else []
    if args.command == "quotes" and not 1 <= len(windows) <= 80:
        raise ValueError("Declare between 1 and 80 bounded quote windows")
    client = new_client()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {"observed_at":datetime.now(timezone.utc).isoformat(), "command":args.command,
                "collector_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "files":[]}
    if args.command == "probe":
        result = probe(client)
        manifest["files"].append(save(args.output / "probe.json", result))
        brief = {name:check if not name.startswith("sip_") else
                 {"status":check["status"], "records":len(check.get("data", {}).get("records") or []),
                  "error":check.get("error")} for name, check in result["checks"].items()}
        print(json.dumps({"observed_at":result["observed_at"], "checks":brief}, indent=2))
    elif args.command == "bars":
        for symbol, timeframe in (("LITE", "1Min"), ("LITE", "5Min"), ("SPY", "5Min")):
            payload = paged(client, f"/v2/stocks/{symbol}/bars",
                {"feed":"sip", "adjustment":"raw", "timeframe":timeframe,
                 "start":"2026-01-01T00:00:00Z", "end":"2026-09-05T00:00:00Z", "sort":"asc", "limit":10000}, "bars")
            manifest["files"].append(save(args.output / f"{symbol}_{timeframe}.json", payload))
            print(json.dumps({"symbol":symbol, "timeframe":timeframe, "rows":len(payload["rows"]),
                              "pages":payload["pages"], "complete":payload["complete"]}), flush=True)
    else:
        for index, window in enumerate(windows):
            if set(window) != {"start", "end"}:
                raise ValueError("Quote windows must contain only start and end")
            start = datetime.fromisoformat(window["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(window["end"].replace("Z", "+00:00"))
            if not start.tzinfo or not end.tzinfo or not 0 < (end-start).total_seconds() <= 120:
                raise ValueError("Quote window must be timezone-aware and at most 120 seconds")
            payload = paged(client, "/v2/stocks/LITE/quotes",
                            {**window, "feed":"sip", "sort":"asc", "limit":10000}, "quotes", max_pages=5)
            manifest["files"].append(save(args.output / f"quotes_{index:03}.json", payload))
            print(json.dumps({"index":index, "rows":len(payload["rows"]), "complete":payload["complete"]}), flush=True)
    save(args.output / "manifest.json", manifest)


if __name__ == "__main__":
    main()
