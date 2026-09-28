"""Temporary/offline demonstration of the isolated $10,000 paper ledgers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path

from .profile import offline_summary


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="agentic-paper-10000-v1-") as temporary:
        summary = offline_summary(
            Path(temporary),
            as_of=datetime(2026, 9, 15, 20, 30, tzinfo=timezone.utc),
        )
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

