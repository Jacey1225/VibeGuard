"""Shallow-cloning a public repository into an ephemeral destination directory."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class CloneFailedError(RuntimeError):
    """Raised when `git clone` exits non-zero for reasons other than a timeout."""


class CloneTimeoutError(RuntimeError):
    """Raised when `git clone` doesn't finish within the configured timeout."""


class GitExecutableNotFoundError(RuntimeError):
    """Raised when no `git` executable can be found on PATH."""


def clone_repository(clone_url: str, destination: Path, timeout_seconds: int) -> None:
    """Shallow-clone `clone_url` into `destination`.

    Uses `--depth 1` to avoid pulling full history, disables submodules
    (a malicious repo's `.gitmodules` could otherwise trigger unbounded
    additional clones), and passes `--` before the URL to guard against
    option injection even though the URL was already validated as a
    github.com repository reference. Resolves `git` to an absolute path
    once via `shutil.which` rather than letting the subprocess search
    PATH itself at call time.

    Raises:
        GitExecutableNotFoundError: if no `git` executable is on PATH.
        CloneTimeoutError: if the clone doesn't finish in time.
        CloneFailedError: if `git clone` exits non-zero for any other
            reason (repo doesn't exist, network failure, etc).
    """
    git_executable = shutil.which("git")
    if git_executable is None:
        raise GitExecutableNotFoundError("no `git` executable found on PATH")

    command = [
        git_executable,
        "clone",
        "--depth",
        "1",
        "--no-tags",
        "--single-branch",
        "--recurse-submodules=no",
        "--",
        clone_url,
        str(destination),
    ]
    try:
        # List-args with shell=False: no shell interpolation of clone_url.
        result = subprocess.run(  # noqa: S603
            command,
            shell=False,
            capture_output=True,
            timeout=timeout_seconds,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired as error:
        raise CloneTimeoutError(f"git clone exceeded {timeout_seconds}s") from error

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        raise CloneFailedError(f"git clone failed: {stderr.strip()}")
