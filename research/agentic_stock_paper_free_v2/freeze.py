"""Verify the immutable free stock-runtime source manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = frozenset({"README.md", "__init__.py", "config.json", "freeze.py", "runner_cli.py", "runtime.py"})


def verify(root: Path = ROOT) -> list[str]:
    path = root / "FREEZE.json"
    if path.is_symlink() or not path.is_file():
        return ["invalid-manifest"]
    try:
        value = json.loads(path.read_text())
        expected = {"schema_version", "package_version", "frozen_at", "change_policy", "hash_algorithm", "files"}
        if set(value) != expected:
            raise ValueError("manifest fields")
        if value["schema_version"] != "1.0" or value["package_version"] != "agentic_stock_paper_free_v2" or value["hash_algorithm"] != "sha256":
            raise ValueError("manifest identity")
        files = value["files"]
        if type(files) is not dict or set(files) != REQUIRED:
            raise ValueError("manifest file set")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [f"invalid-manifest:{exc}"]
    errors = []
    for name, expected_hash in sorted(files.items()):
        target = root / name
        if target.is_symlink() or not target.is_file():
            errors.append(f"missing-or-symlink:{name}")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            errors.append(f"drift:{name}")
    actual = {path.name for path in root.iterdir() if path.is_file() and path.name != "FREEZE.json" and not path.name.startswith("test_")}
    errors.extend(f"untracked-runtime:{name}" for name in sorted(actual - REQUIRED))
    return errors


if __name__ == "__main__":
    errors = verify()
    if errors:
        raise SystemExit("freeze verification failed: " + ", ".join(errors))
    print("AGENTIC_STOCK_PAPER_FREE_V2_FREEZE_OK")
