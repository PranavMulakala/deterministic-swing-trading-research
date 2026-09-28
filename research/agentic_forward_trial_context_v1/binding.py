"""Verify exact frozen dependencies before importing their executable code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class BindingError(ValueError):
    pass


CORE_MANIFEST_SHA256 = "e6d3961f98830ef46850f194ae77f7486714faac685bd6acd77a8a496ecf488d"
PROFILE_MANIFEST_SHA256 = "84f7e5a765e2d86ec3f10020ef5a2119248cc881871c8f8b92febd65a2013b2d"
CORE_FILES = frozenset({
    "ARCHITECTURE.md", "PROTOCOL.md", "README.md", "THIRD_PARTY.md", "__init__.py",
    "broker_handoff.py", "broker_handoff_schema.json", "common.py", "config.json",
    "config.py", "controller.py", "council.py", "decisions.py", "demo.py", "evidence.py",
    "freeze.py", "options.py", "risk.py", "risk_policy.json", "stock.py",
})
PROFILE_FILES = frozenset({
    "PROTOCOL.md", "README.md", "__init__.py", "config.json", "demo.py", "freeze.py", "profile.py",
})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plain_object(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict or not all(isinstance(k, str) for k in value):
        raise BindingError(f"{field} must be a plain JSON object")
    return value


def _verify_package(directory: Path, expected_manifest: str, required: frozenset[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise BindingError(f"frozen package directory is absent or unsafe: {directory.name}")
    manifest_path = directory / "FREEZE.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise BindingError(f"missing safe manifest: {directory.name}")
    if _sha256(manifest_path) != expected_manifest:
        raise BindingError(f"frozen manifest hash mismatch: {directory.name}")
    try:
        manifest = _plain_object(json.loads(manifest_path.read_text(encoding="utf-8")), "manifest")
        files = _plain_object(manifest["files"], "manifest.files")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        raise BindingError(f"invalid frozen manifest: {directory.name}") from exc
    if set(files) != required:
        raise BindingError(f"frozen manifest coverage mismatch: {directory.name}")
    for relative, expected_hash in files.items():
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise BindingError(f"invalid frozen file hash: {directory.name}/{relative}")
        path = directory / relative
        if path.is_symlink() or not path.is_file() or path.parent != directory:
            raise BindingError(f"missing or unsafe frozen file: {directory.name}/{relative}")
        if _sha256(path) != expected_hash:
            raise BindingError(f"frozen file drift: {directory.name}/{relative}")


def verify_frozen_bindings(repo_root: Path | None = None) -> dict[str, str]:
    """Fail closed unless both upstream versioned packages exactly match their pins."""
    repo = (Path(__file__).resolve().parents[2] if repo_root is None else Path(repo_root).resolve())
    research = repo / "research"
    _verify_package(research / "agentic_portfolio_v1", CORE_MANIFEST_SHA256, CORE_FILES)
    _verify_package(
        research / "agentic_portfolio_paper_10000_v1", PROFILE_MANIFEST_SHA256, PROFILE_FILES
    )
    return {
        "agentic_portfolio_v1_manifest_sha256": CORE_MANIFEST_SHA256,
        "agentic_portfolio_paper_10000_v1_manifest_sha256": PROFILE_MANIFEST_SHA256,
    }
