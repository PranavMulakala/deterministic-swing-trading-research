"""Direct-breakout signal preparation; execution stays in frozen ORB quote v2."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from research.orb_comparison_v1 import engine as parent


ZERO = Decimal("0")


def _at(day: str, hm: str) -> datetime:
    return parent.at(day, hm)


def direct_pattern(feature: dict[str, Any], rows: dict[datetime, dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    """Return the first completed five-minute close above the opening high.

    The returned ``time`` is the first instant when the breakout bar is complete.
    No retest is observed or required.  Missing bars fail closed.
    """
    high = Decimal(str(feature["high"]))
    low = Decimal(str(feature["low"]))
    stop = (high + low) / 2 - Decimal("0.01")
    stamp = _at(feature["day"], spec["selection"]["range_end_exclusive"])
    deadline = _at(feature["day"], spec["pattern"]["last_confirmation_close"])
    while stamp + timedelta(minutes=5) <= deadline:
        row = rows.get(stamp)
        if row is None:
            return {"status": "unknown_pattern_gap", "time": stamp}
        close = Decimal(str(row["c"]))
        if close > high:
            decision_time = stamp + timedelta(minutes=5)
            return {
                "status": "signal",
                "time": decision_time,
                "stop": stop,
                "confirmation_close": close,
                "breakout_time": decision_time,
            }
        stamp += timedelta(minutes=5)
    return {"status": "no_breakout"}


def prepare(
    spec: dict[str, Any],
    sessions: dict[str, tuple[datetime, datetime]],
    bars: dict[tuple[str, int], dict[str, dict[datetime, dict[str, Any]]]],
    actions: dict[str, set[str]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Reuse every parent eligibility input and change only the entry pattern."""
    days = list(sessions)
    prepared: dict[str, dict[str, dict[str, Any]]] = {}
    for index, day in enumerate(days):
        if not spec["evaluation_start"] <= day <= spec["evaluation_end"]:
            continue
        prepared[day] = {}
        for symbol in spec["symbols"]:
            feature = parent.features(symbol, index, days, sessions, bars, actions, spec)
            if feature["status"] == "eligible":
                feature["pattern"] = direct_pattern(feature, bars[symbol, 5][day], spec)
            prepared[day][symbol] = feature
    return prepared


def assert_only_pattern_changed(
    retest: dict[str, dict[str, dict[str, Any]]],
    direct: dict[str, dict[str, dict[str, Any]]],
) -> None:
    """Prove eligibility and lagged features are identical before execution."""
    if set(retest) != set(direct):
        raise ValueError("direct challenger date population differs from parent")
    for day in retest:
        if set(retest[day]) != set(direct[day]):
            raise ValueError("direct challenger symbol population differs from parent")
        for symbol in retest[day]:
            left = deepcopy(retest[day][symbol])
            right = deepcopy(direct[day][symbol])
            left.pop("pattern", None)
            right.pop("pattern", None)
            if left != right:
                raise ValueError(f"non-pattern feature drift: {day}:{symbol}")

