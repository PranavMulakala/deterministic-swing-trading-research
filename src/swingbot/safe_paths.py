from __future__ import annotations

import os
import stat
from pathlib import Path


class UnsafePathError(PermissionError):
    pass


def require_no_symlink_components(path: str | Path, *, label: str) -> Path:
    """Return an absolute lexical path after rejecting symlinked components.

    macOS exposes root-owned compatibility aliases such as /var -> /private/var.
    Those immutable root-level aliases are accepted; user-controlled aliases at
    every deeper level are rejected before sensitive files are opened or chmodded.
    """
    candidate = Path(os.path.abspath(os.fspath(path)))
    current = Path(candidate.anchor)
    for component in candidate.parts[1:]:
        current /= component
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        if not stat.S_ISLNK(metadata.st_mode):
            continue
        root_owned_system_alias = (
            current.parent == Path(candidate.anchor)
            and metadata.st_uid == 0
        )
        if not root_owned_system_alias:
            raise UnsafePathError(f"{label} may not traverse a symbolic link")
    return candidate
