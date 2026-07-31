"""Tests for the clone-root containment guard (zip-slip/symlink-escape defense)."""

from pathlib import Path

import pytest

from vibeguard.adapters.filesystem.path_containment import (
    PathEscapesCloneRootError,
    resolve_within_clone_root,
)


def test_resolve_within_clone_root_accepts_path_inside_root(tmp_path: Path):
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    candidate = clone_root / "src" / "app.py"
    candidate.parent.mkdir()
    candidate.write_text("x")

    resolved = resolve_within_clone_root(clone_root, candidate)
    assert resolved == candidate.resolve()


def test_resolve_within_clone_root_accepts_the_root_itself(tmp_path: Path):
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    resolved = resolve_within_clone_root(clone_root, clone_root)
    assert resolved == clone_root.resolve()


def test_resolve_within_clone_root_rejects_dotdot_escape(tmp_path: Path):
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    escaping_candidate = clone_root / ".." / "outside.txt"

    with pytest.raises(PathEscapesCloneRootError):
        resolve_within_clone_root(clone_root, escaping_candidate)


def test_resolve_within_clone_root_rejects_symlink_escape(tmp_path: Path):
    clone_root = tmp_path / "clone"
    clone_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = clone_root / "escape.txt"
    link.symlink_to(outside)

    with pytest.raises(PathEscapesCloneRootError):
        resolve_within_clone_root(clone_root, link)
