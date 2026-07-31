"""Guarding against a cloned file's path escaping the clone root."""

from pathlib import Path


class PathEscapesCloneRootError(ValueError):
    """Raised when a candidate path resolves outside the clone root."""


def resolve_within_clone_root(clone_root: Path, candidate: Path) -> Path:
    """Resolve `candidate` and verify it stays within `clone_root`.

    Defends against a maliciously crafted repository containing a
    symlink that would otherwise let a file read escape the intended
    clone directory (the zip-slip/symlink-escape class of attack),
    even though `walk_clone_tree` already skips symlinks at the
    directory-entry level — this is a second, independent check applied
    directly to the resolved path.

    Raises:
        PathEscapesCloneRootError: if the resolved path isn't contained
            within the resolved clone root.
    """
    resolved_root = clone_root.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_root):
        raise PathEscapesCloneRootError(f"{candidate} resolves outside {clone_root}")
    return resolved_candidate
