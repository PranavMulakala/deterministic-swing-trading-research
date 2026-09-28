"""Verify the immutable paper-runtime source manifest."""

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
        if set(value) != {"schema_version", "package_version", "frozen_at", "change_policy", "hash_algorithm", "files"}:
            raise ValueError("manifest fields")
        if value["schema_version"] != "1.0" or value["package_version"] != "agentic_paper_runtime_v1" or value["hash_algorithm"] != "sha256":
            raise ValueError("manifest identity")
        files = value["files"]
        if type(files) is not dict or set(files) != REQUIRED:
            raise ValueError("manifest file set")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [f"invalid-manifest:{exc}"]
    errors = []
    for name, expected in sorted(files.items()):
        target = root / name
        if target.is_symlink() or not target.is_file():
            errors.append(f"missing-or-symlink:{name}")
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            errors.append(f"drift:{name}")
    actual = {p.name for p in root.iterdir() if p.is_file() and p.name != "FREEZE.json" and not p.name.startswith("test_")}
    errors.extend(f"untracked-runtime:{name}" for name in sorted(actual - REQUIRED))
    return errors


if __name__ == "__main__":
    errors = verify()
    if errors:
        raise SystemExit("freeze verification failed: " + ", ".join(errors))
    print("AGENTIC_PAPER_RUNTIME_V1_FREEZE_OK")
