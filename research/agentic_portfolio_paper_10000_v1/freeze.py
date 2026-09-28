"""Verify the immutable file manifest for the $10,000 paper profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = frozenset({
    "PROTOCOL.md", "README.md", "__init__.py", "config.json", "demo.py", "freeze.py", "profile.py",
})


def verify(root: Path = ROOT) -> list[str]:
    manifest_path = root / "FREEZE.json"
    errors: list[str] = []
    if manifest_path.is_symlink():
        return ["invalid-manifest:FREEZE.json must not be a symlink"]
    if not manifest_path.is_file():
        return ["invalid-manifest:FREEZE.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if type(manifest) is not dict or set(manifest) != {
            "schema_version", "package_version", "frozen_at", "change_policy", "hash_algorithm", "files",
        }:
            raise ValueError("manifest fields do not match the frozen schema")
        if manifest["schema_version"] != "1.0" or manifest["package_version"] != "agentic_portfolio_paper_10000_v1":
            raise ValueError("manifest identity differs")
        if manifest["hash_algorithm"] != "sha256":
            raise ValueError("hash_algorithm must be sha256")
        files = manifest["files"]
        if type(files) is not dict or not all(
            isinstance(name, str) and Path(name).name == name
            and isinstance(digest, str) and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
            for name, digest in files.items()
        ):
            raise ValueError("files must be a top-level lowercase SHA-256 map")
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
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
        if relative not in REQUIRED_FILES:
            continue
        target = root / relative
        if target.is_symlink() or not target.is_file():
            errors.append(f"missing-or-symlink:{relative}")
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"drift:{relative}")
    return errors


def main() -> None:
    errors = verify()
    if errors:
        raise SystemExit("freeze verification failed: " + ", ".join(errors))
    print("PAPER_10000_FREEZE_OK")


if __name__ == "__main__":
    main()
