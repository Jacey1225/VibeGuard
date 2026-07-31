"""Tests for the shallow-clone adapter, against a local bare repo (never real GitHub)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from vibeguard.adapters.github.clone import CloneFailedError, CloneTimeoutError, clone_repository


def test_clone_repository_happy_path_shallow_clones_local_bare_repo(
    local_bare_repo: Path, tmp_path: Path
):
    destination = tmp_path / "clone-dest"
    # git ignores --depth for a plain local path ("use file:// instead");
    # the file:// form is what actually exercises the shallow-clone flag.
    clone_repository(f"file://{local_bare_repo}", destination, timeout_seconds=30)

    assert (destination / "README.md").exists()
    assert (destination / "src" / "app.py").exists()
    assert (destination / ".git" / "shallow").exists()


def test_clone_repository_nonexistent_source_raises_clone_failed(tmp_path: Path):
    destination = tmp_path / "clone-dest"
    with pytest.raises(CloneFailedError):
        clone_repository(str(tmp_path / "does-not-exist"), destination, timeout_seconds=30)


def test_clone_repository_timeout_raises_clone_timeout_error(local_bare_repo: Path, tmp_path: Path):
    destination = tmp_path / "clone-dest"
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=1)):
        with pytest.raises(CloneTimeoutError):
            clone_repository(str(local_bare_repo), destination, timeout_seconds=1)


def test_clone_repository_invokes_subprocess_with_list_args_and_no_shell(
    local_bare_repo: Path, tmp_path: Path
):
    destination = tmp_path / "clone-dest"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=b"", stderr=b""
        )
        clone_repository(str(local_bare_repo), destination, timeout_seconds=30)

    args, kwargs = mock_run.call_args
    command = args[0]
    assert isinstance(command, list)
    assert kwargs["shell"] is False
