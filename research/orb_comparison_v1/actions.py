"""Supplement frozen bars with allowlisted corporate-action and asset GETs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from swingbot.alpaca_paper import AlpacaPaperClient
from swingbot.paper_cli import _load_env
from .collect import ROOT, SYMBOLS, digest, save

QUERY = {"symbols": ",".join(SYMBOLS), "start": "2025-10-01", "end": "2026-09-07", "limit": 1000, "sort": "asc"}


class ActionClient(AlpacaPaperClient):
    def _request(self, method, path, *, data_api=False, query=None, **kwargs):
        allowed = path == "/v1/corporate-actions" if data_api else path in {f"/v2/assets/{s}" for s in SYMBOLS}
        if method != "GET" or kwargs or not allowed:
            raise ValueError("Only corporate-action and scoped asset GETs permitted")
        return super()._request(method, path, data_api=data_api, query=query)


def fetch(client):
    pages, seen, token = [], set(), None
    for _ in range(20):
        result = client._request("GET", "/v1/corporate-actions", data_api=True,
                                 query={**QUERY, **({"page_token": token} if token else {})})
        if not isinstance(result, dict) or not isinstance(result.get("corporate_actions"), dict):
            raise ValueError("Invalid action response")
        if any(not isinstance(rows, list) for rows in result["corporate_actions"].values()):
            raise ValueError("Invalid action arrays")
        pages.append(result)
        token = result.get("next_page_token")
        if token is None:
            break
        if not isinstance(token, str) or not token or token in seen:
            raise ValueError("Stalled action pagination")
        seen.add(token)
    else:
        raise ValueError("Action pagination incomplete")
    assets = {}
    for symbol in SYMBOLS:
        asset = client._request("GET", f"/v2/assets/{symbol}")
        if not isinstance(asset, dict) or asset.get("symbol") != symbol:
            raise ValueError("Asset identity mismatch")
        assets[symbol] = {k: asset.get(k) for k in ("symbol", "name", "class", "exchange", "status")}
    return {"complete": True, "query": QUERY, "pages": pages, "assets_current_not_point_in_time": assets,
            "fetched_at": datetime.now(timezone.utc).isoformat(), "collector_sha256": digest(__file__)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _load_env(ROOT / ".env")
    client = ActionClient(os.environ.get("ALPACA_PAPER_API_KEY", ""), os.environ.get("ALPACA_PAPER_API_SECRET", ""))
    try:
        result = fetch(client)
    except Exception as exc:
        print(json.dumps({"complete": False, "error_type": type(exc).__name__, "detail": "Provider body suppressed"}))
        return 1
    print(json.dumps(save(args.output, result)))
    print(json.dumps({"counts": [{k: len(v) for k, v in p["corporate_actions"].items()} for p in result["pages"]],
                      "assets": result["assets_current_not_point_in_time"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
