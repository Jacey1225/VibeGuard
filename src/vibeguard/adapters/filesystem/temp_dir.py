"""Ephemeral clone-directory lifecycle."""

import shutil
import tempfile
from pathlib import Path


def create_ephemeral_clone_dir() -> Path:
    """Create a fresh, empty temporary directory to clone into."""
    return Path(tempfile.mkdtemp(prefix="vibeguard-clone-"))


def remove_clone_dir(path: Path) -> None:
    """Remove a clone directory and everything in it, if it exists."""
    shutil.rmtree(path, ignore_errors=True)
