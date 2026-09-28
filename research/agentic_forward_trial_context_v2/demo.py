"""Safe demonstration: missing real inputs must produce BLOCKED_DATA, never orders."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .runner import ForwardTrialRunner, build_trial


def main() -> int:
    decision_at = datetime(2026, 9, 17, 19, 30, tzinfo=timezone.utc)
    with TemporaryDirectory(prefix="forward-context-demo-") as folder:
        runner = ForwardTrialRunner(build_trial(Path(folder)))
        stock = runner.evaluate_stock_pair(
            price_receipt=None, decision_at=decision_at, idempotency_key="demo-stock-missing",
        )
        option = runner.evaluate_option_pair(
            chain_receipt=None, decision_at=decision_at, idempotency_key="demo-option-missing",
        )
        output = {
            "mode": "PAPER_ONLY_NO_ORDER",
            "stock": {arm: result.receipt["action"] for arm, result in stock.items()},
            "options": {arm: result.receipt["action"] for arm, result in option.items()},
            "state_location": "temporary directory removed on exit",
        }
        print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

