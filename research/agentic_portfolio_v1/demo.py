"""Synthetic, temporary, offline demonstration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import tempfile

from .controller import make_card, make_receipt
from .evidence import EvidencePacket
from .risk import RiskLedger
from .stock import STRATEGY, VERSION, StockSwingEngine


def main() -> None:
    now = datetime(2026, 9, 14, 20, 0, tzinfo=timezone.utc)
    packet = EvidencePacket.build(
        kind="stock_entry", strategy=STRATEGY, version=VERSION, symbol="LITE", source="SYNTHETIC_DEMO",
        feature_as_of=now - timedelta(minutes=2), observed_at=now - timedelta(minutes=1), retrieved_at=now,
        data={
            "price": "100", "next_ask": "100.05", "entry_limit": "100.10",
            "dollar_volumes_20": ["60000000"] * 20, "atr14": "5",
            "session_return": "-0.04", "session_vwap": "99", "sma50": "95",
            "earnings_sessions_away": 8, "hard_adverse_news": False, "thesis_broken": False,
            "thesis": "synthetic qualifying reversal", "invalidation": "thesis_broken evidence",
        },
    )
    with tempfile.TemporaryDirectory(prefix="agentic-portfolio-demo-") as tmp:
        ledger = RiskLedger(f"{tmp}/stock.sqlite", "stock-demo-1000", Decimal("1000"))
        decision = StockSwingEngine(ledger).evaluate_entry(packet, now, "demo-intent-1")
        card = make_card(decision, packet, now, expected_virtual_account=ledger.account_id)
        print(json.dumps(make_receipt(card), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
