"""Scheduled fail-closed entrypoint for the offline paper lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import RuntimeBlocked, atomic_write, blocked_status, process_cycle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("/var/lib/agentic-paper-input/latest.json"))
    parser.add_argument("--state", type=Path, default=Path("/var/lib/agentic-paper-runtime"))
    parser.add_argument("--status", type=Path, default=Path("/var/lib/agentic-paper-runtime/status.json"))
    args = parser.parse_args()
    try:
        if not args.input.is_file() or args.input.is_symlink():
            raise RuntimeBlocked("no validated provider cycle is available")
        raw = args.input.read_bytes()
        if len(raw) > 64 * 1024 * 1024:
            raise RuntimeBlocked("provider cycle exceeds 64 MiB")
        result = process_cycle(json.loads(raw), args.state)
        code = 0
    except (RuntimeBlocked, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        result = blocked_status(str(exc))
        code = 0
    atomic_write(args.status, result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

