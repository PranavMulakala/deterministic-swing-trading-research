"""Verify the complete immutable runtime/specification manifest for this version."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = frozenset({
    "ARCHITECTURE.md", "DATA_CONTRACT.md", "PROTOCOL.md", "README.md", "__init__.py",
    "binding.py", "config.json", "context.py", "data_gap_snapshot.json", "demo.py",
    "deployment/README.md", "freeze.py", "macro.py",
    "macro_calendar.json", "observer.py", "receipts.py", "runner.py", "sector_mapping.json",
})


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root: Path | None = None) -> list[str]:
    package = ROOT if root is None else Path(root)
    errors: list[str] = []
    manifest_path = package / "FREEZE.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return ["FREEZE.json missing or unsafe"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["FREEZE.json invalid"]
    expected_top = {
        "schema_version", "package_version", "frozen_at", "change_policy", "hash_algorithm", "files",
    }
    if type(manifest) is not dict or set(manifest) != expected_top:
        return ["manifest fields mismatch"]
    if (manifest["schema_version"] != "1.0"
            or manifest["package_version"] != "agentic_forward_trial_context_v3"
            or manifest["hash_algorithm"] != "sha256"):
        errors.append("manifest identity mismatch")
    files = manifest.get("files")
    if type(files) is not dict:
        return errors + ["manifest files invalid"]
    if set(files) != REQUIRED_FILES:
        errors.append("manifest required-file coverage mismatch")
    actual_runtime = {
        str(path.relative_to(package)) for path in package.rglob("*")
        if path.is_file() and path.name != "FREEZE.json"
        and not path.name.startswith("test_") and "__pycache__" not in path.parts
    }
    if actual_runtime != REQUIRED_FILES:
        errors.append("runtime/specification file set mismatch")
    for relative in sorted(REQUIRED_FILES):
        path = package / relative
        expected = files.get(relative)
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing or unsafe file: {relative}")
        elif not isinstance(expected, str) or len(expected) != 64 or _sha(path) != expected:
            errors.append(f"hash mismatch: {relative}")
    return errors


def main() -> int:
    errors = verify()
    if errors:
        print("FREEZE_FAILED: " + "; ".join(errors))
        return 1
    print("FORWARD_CONTEXT_V3_FREEZE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
