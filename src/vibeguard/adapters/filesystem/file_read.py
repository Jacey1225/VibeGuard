"""Bounded reads of a candidate file's size, sample, and full contents."""

from pathlib import Path

_BINARY_SNIFF_SAMPLE_SIZE = 8000


def read_file_size(path: Path) -> int:
    """Return a file's size in bytes without reading its contents."""
    return path.stat().st_size


def read_file_sample(path: Path) -> bytes:
    """Read a small sample from the start of a file, for binary sniffing."""
    with path.open("rb") as handle:
        return handle.read(_BINARY_SNIFF_SAMPLE_SIZE)


def read_file_contents(path: Path, max_bytes: int) -> bytes:
    """Read a file's full contents, defensively re-checking the size bound.

    Callers are expected to have already checked `read_file_size` against
    the same `max_bytes` before calling this. Re-enforcing the bound here
    against what's actually read guards against a file that changed size
    between the check and the read (TOCTOU).

    Raises:
        ValueError: if more than `max_bytes` was read.
    """
    with path.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"{path} exceeds the {max_bytes}-byte read bound")
    return data
