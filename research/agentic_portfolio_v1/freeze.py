"""Verify the immutable file manifest for this package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = frozenset({
    "ARCHITECTURE.md", "PROTOCOL.md", "README.md", "THIRD_PARTY.md", "__init__.py",
    "broker_handoff.py", "broker_handoff_schema.json", "common.py", "config.json", "config.py",
    "controller.py", "council.py", "decisions.py", "demo.py", "evidence.py", "freeze.py",
    "options.py", "risk.py", "risk_policy.json", "stock.py",
})


def verify(root: Path = ROOT) -> list[str]:
    manifest_path = root / "FREEZE.json"
    errors: list[str] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest["files"]
        if type(files) is not dict or not all(isinstance(k, str) and isinstance(v, str) for k, v in files.items()):
            raise ValueError("files must be a string map")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"invalid-manifest:{exc}"]
    listed = set(files)
    for relative in sorted(REQUIRED_FILES - listed):
        errors.append(f"omitted-from-manifest:{relative}")
    for relative in sorted(listed - REQUIRED_FILES):
        errors.append(f"unexpected-in-manifest:{relative}")
    actual_runtime = {
        path.name for path in root.iterdir()
        if path.is_file() and path.name != "FREEZE.json" and not path.name.startswith("test_")
    }
    for relative in sorted(REQUIRED_FILES - actual_runtime):
        errors.append(f"missing-required:{relative}")
    for relative in sorted(actual_runtime - REQUIRED_FILES):
        errors.append(f"untracked-runtime:{relative}")
    for relative, expected in sorted(files.items()):
        if relative not in REQUIRED_FILES or Path(relative).name != relative:
            continue
        target = root / relative
        if not target.is_file():
            errors.append(f"missing:{relative}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"drift:{relative}")
    return errors


def main() -> None:
    errors = verify()
    if errors:
        raise SystemExit("freeze verification failed: " + ", ".join(errors))
    print("FREEZE_OK")


if __name__ == "__main__":
    main()
