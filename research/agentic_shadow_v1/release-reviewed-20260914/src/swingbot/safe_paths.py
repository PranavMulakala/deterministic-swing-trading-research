from __future__ import annotations

import os
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


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


class PrivateDirectory:
    """Filesystem operations relative to a pinned directory, never a path alias."""

    def __init__(self, descriptor: int, path: Path, label: str):
        self.descriptor = descriptor
        self.path = path
        self.label = label

    def check_leaf(self, name: str) -> None:
        if Path(name).name != name or name in {"", ".", ".."}:
            raise UnsafePathError(f"{self.label} has an invalid filename")
        try:
            metadata = os.stat(name, dir_fd=self.descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise UnsafePathError(f"{self.label} must be a regular file without links")
        if metadata.st_uid != os.getuid():
            raise UnsafePathError(f"{self.label} must be owned by the current user")

    def open_file(self, name: str, flags: int) -> int:
        self.check_leaf(name)
        descriptor = os.open(
            name, flags | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600, dir_fd=self.descriptor,
        )
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
            ):
                raise UnsafePathError(f"{self.label} must be an owner-controlled regular file")
            os.fchmod(descriptor, 0o600)
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def read(self, name: str) -> bytes:
        with os.fdopen(self.open_file(name, os.O_RDONLY), "rb") as stream:
            return stream.read()

    def replace(self, name: str, contents: bytes) -> None:
        self.check_leaf(name)
        temporary = f".{name}.{uuid.uuid4().hex}.tmp"
        try:
            descriptor = self.open_file(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())
            self.check_leaf(name)
            os.replace(
                temporary, name,
                src_dir_fd=self.descriptor, dst_dir_fd=self.descriptor,
            )
            os.fsync(self.descriptor)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.descriptor)
            except FileNotFoundError:
                pass


@contextmanager
def private_parent(path: str | Path, *, label: str) -> Iterator[PrivateDirectory]:
    """Walk with openat/O_NOFOLLOW and pin the parent before any sensitive I/O.

    Only root-owned aliases immediately under / may be followed. Renaming an
    already opened ancestor cannot redirect any subsequent descriptor-relative
    mkdir, chmod, open, unlink or replace operation.
    """
    candidate = require_no_symlink_components(path, label=label)
    descriptor = os.open(candidate.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            for index, component in enumerate(candidate.parts[1:-1]):
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                try:
                    metadata = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o700, dir_fd=descriptor)
                    except FileExistsError:
                        pass  # A competing creator still has to pass openat below.
                else:
                    if index == 0 and stat.S_ISLNK(metadata.st_mode) and metadata.st_uid == 0:
                        flags &= ~os.O_NOFOLLOW
                next_descriptor = os.open(component, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = next_descriptor
            directory = PrivateDirectory(descriptor, candidate.parent, label)
            directory.check_leaf(candidate.name)
            if os.fstat(descriptor).st_uid != os.getuid():
                raise UnsafePathError(f"{label} parent must be owned by the current user")
            os.fchmod(descriptor, 0o700)
        except OSError as exc:
            if isinstance(exc, UnsafePathError):
                raise
            raise UnsafePathError(f"{label} could not be opened without following links") from exc
        yield directory
    finally:
        os.close(descriptor)
