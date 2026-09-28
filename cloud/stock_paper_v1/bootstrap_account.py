"""One-time, GET-only paper-account lock for the stock alert service."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

from research.alpaca_stock_paper_v1.read_only import HttpsGet, PaperReader, URLS
from research.alpaca_stock_paper_v1.worker import _private_json


CONFIG = Path("/etc/stock-paper-alerts/config.json")


def main() -> None:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        raise RuntimeError("systemd_credentials_required")
    secret = _private_json(str(Path(directory) / "alpaca-paper"), systemd_credential=True)
    if set(secret) != {"key", "secret"} or not all(isinstance(secret[k], str) and secret[k] for k in secret):
        raise RuntimeError("paper_credential_invalid")
    if not secret["key"].startswith("PK"):
        raise RuntimeError("paper_credential_required")
    fetch = HttpsGet(key_id=secret["key"], secret_key=secret["secret"])
    account = fetch(URLS["account"])
    if not isinstance(account, dict) or account.get("status") != "ACTIVE":
        raise RuntimeError("paper_account_inactive")
    account_id = account.get("id")
    if not isinstance(account_id, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", account_id):
        raise RuntimeError("paper_account_id_invalid")

    config = _private_json(str(CONFIG))
    if config.get("version") != 1 or config.get("position_card") is not None:
        raise RuntimeError("unexpected_stock_config")
    if config.get("paper_account_id") not in (None, account_id):
        raise RuntimeError("paper_account_mismatch")

    snapshot = PaperReader(fetch).snapshot(expected_account_id=account_id)
    print(json.dumps({"status": "paper_read_ok", "positions": len(snapshot.positions),
                      "open_orders": len(snapshot.open_order_ids),
                      "market_open": snapshot.market_open}, sort_keys=True))
    if config.get("paper_account_id") == account_id:
        return

    config["paper_account_id"] = account_id
    fd, name = tempfile.mkstemp(prefix=".config-", dir=CONFIG.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, CONFIG)
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # The read client sanitizes network errors. Keep all other failures generic.
        print(json.dumps({"status": "paper_read_failed", "reason": type(exc).__name__}))
        raise SystemExit(1)
