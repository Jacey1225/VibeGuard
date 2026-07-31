"""Tests for walking a cloned tree with excluded-directory pruning."""

import os
from pathlib import Path

from vibeguard.adapters.filesystem.tree_walk import walk_clone_tree


def test_walk_clone_tree_yields_regular_files(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("b")

    found = {str(path.relative_to(tmp_path)) for path in walk_clone_tree(tmp_path)}
    assert found == {"a.txt", os.path.join("sub", "b.txt")}


def test_walk_clone_tree_never_descends_into_excluded_directories(tmp_path: Path):
    excluded = tmp_path / ".git"
    excluded.mkdir()
    sentinel = excluded / "sentinel"
    sentinel.write_text("would raise if read")
    # Make the sentinel unreadable to prove it's genuinely never touched,
    # not just filtered out of the result after being read.
    sentinel.chmod(0o000)

    (tmp_path / "kept.txt").write_text("kept")

    try:
        found = {str(path.relative_to(tmp_path)) for path in walk_clone_tree(tmp_path)}
    finally:
        sentinel.chmod(0o644)

    assert found == {"kept.txt"}


def test_walk_clone_tree_skips_symlinked_files(tmp_path: Path):
    target = tmp_path / "real.txt"
    target.write_text("real")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    found = {str(path.relative_to(tmp_path)) for path in walk_clone_tree(tmp_path)}
    assert found == {"real.txt"}
