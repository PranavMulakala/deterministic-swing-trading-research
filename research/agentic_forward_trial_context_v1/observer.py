"""Fail-closed readiness observer; it reads hashes and prints JSON, never decisions or orders."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .binding import verify_frozen_bindings


def readiness(repo_root: Path | None = None) -> dict[str, Any]:
    from .freeze import verify as verify_self
    repo = Path(__file__).resolve().parents[2] if repo_root is None else Path(repo_root).resolve()
    snapshot = json.loads(Path(__file__).with_name("data_gap_snapshot.json").read_text(encoding="utf-8"))
    reasons = list(snapshot["measured_or_code_visible_gaps"])
    self_freeze = verify_self()
    if self_freeze:
        reasons.append("forward-trial package freeze failed: " + "; ".join(self_freeze))
    source_status: dict[str, str] = {}
    for relative, expected in snapshot["sources"].items():
        path = repo / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() and not path.is_symlink() else None
        source_status[relative] = "MATCH" if actual == expected else "MISSING_OR_DRIFTED"
        if actual != expected:
            reasons.append(f"source missing or drifted: {relative}")
    try:
        bindings = verify_frozen_bindings(repo)
    except Exception as exc:
        bindings = {"status": "FAILED", "reason": str(exc)}
        reasons.append("frozen dependency binding failed")
    return {
        "schema_version": "1.0", "package": "agentic_forward_trial_context_v1",
        "mode": "ENTRY_GATE_ONLY_BLOCKED", "overall": "BLOCKED",
        "orders_enabled": False, "network_enabled": False, "model_calls_enabled": False,
        "source_status": source_status, "self_freeze": "OK" if not self_freeze else "FAILED",
        "frozen_bindings": bindings,
        "per_arm": {name: {"status": "BLOCKED_DATA", "missing": gaps}
                    for name, gaps in snapshot["per_arm"].items()},
        "reasons": reasons,
        "next_gate": "A new version needs complete point-in-time inputs and a full modeled lifecycle.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(readiness(args.repo_root), sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
