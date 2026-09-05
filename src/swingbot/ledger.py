from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


def deterministic_timestamp(day: date, phase: str = "close") -> str:
    clock = {"open": "14:30:00Z", "intraday": "18:00:00Z", "close": "21:00:00Z"}[phase]
    return f"{day.isoformat()}T{clock}"


class EventLedger:
    """Append-only within one deterministic run; events are never mutated."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._events: list[dict[str, Any]] = []

    def append(self, day: date, event_type: str, *, phase: str = "close", **fields: Any) -> None:
        event = {
            "seq": len(self._events) + 1,
            "run_id": self.run_id,
            "timestamp": deterministic_timestamp(day, phase),
            "event_type": event_type,
            **fields,
        }
        self._events.append(event)

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for event in self._events:
                handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")

