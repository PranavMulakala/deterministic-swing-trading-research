"""One-time GET-only LITE data-feed check; prints metadata, never prices or keys."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from research.alpaca_stock_paper_v1.read_only import HttpsGet, URLS
from research.alpaca_stock_paper_v1.worker import _private_json


def main() -> None:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        raise RuntimeError("systemd_credentials_required")
    secret = _private_json(str(Path(directory) / "alpaca-paper"), systemd_credential=True)
    if set(secret) != {"key", "secret"} or not secret["key"].startswith("PK"):
        raise RuntimeError("paper_credential_required")
    fetch = HttpsGet(key_id=secret["key"], secret_key=secret["secret"])
    quote = fetch(URLS["lite_quote"])["quote"]
    quoted_at = datetime.fromisoformat(quote["t"].replace("Z", "+00:00"))
    if quoted_at.tzinfo is None or float(quote["bp"]) <= 0 or float(quote["ap"]) < float(quote["bp"]):
        raise RuntimeError("invalid_iex_quote")
    age = (datetime.now(timezone.utc) - quoted_at).total_seconds()
    news = fetch(URLS["lite_news"])
    if not isinstance(news, dict) or not isinstance(news.get("news"), list):
        raise RuntimeError("invalid_news_page")
    print(json.dumps({"status": "feed_read_ok", "iex_quote_age_seconds": round(age),
                      "news_items_on_first_page": len(news["news"]),
                      "news_more_pages": bool(news.get("next_page_token"))}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "feed_read_failed", "reason": type(exc).__name__}))
        raise SystemExit(1)
