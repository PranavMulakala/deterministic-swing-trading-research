"""Create or verify the direct-breakout package manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "FREEZE.json"
FILES = ("__init__.py", "engine.py", "config.json", "PROTOCOL.md", "test_direct.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value() -> dict:
    return {
        "schema_version": "1.0",
        "package_version": "orb_direct_breakout_v1",
        "frozen_at": "2026-09-15T23:00:00-07:00",
        "change_policy": "new version required",
        "hash_algorithm": "sha256",
        "files": {name: digest(ROOT / name) for name in FILES},
    }


def verify() -> list[str]:
    try:
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"manifest unreadable: {type(exc).__name__}"]
    expected = value()
    errors = []
    if current != expected:
        errors.append("manifest or pinned file hashes differ")
    runtime = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != "FREEZE.json"}
    if runtime != set(FILES) | {"freeze.py"}:
        errors.append("unexpected package file set")
    return errors


def main() -> int:
    raw = json.dumps(value(), sort_keys=True, indent=2) + "\n"
    MANIFEST.write_text(raw, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

