"""Per-file classification of a candidate file as stored or skipped."""

from dataclasses import dataclass

from vibeguard.core.repository_status import SkipReason

_BINARY_SNIFF_SAMPLE_SIZE = 8000


@dataclass(frozen=True)
class StoredFile:
    """A file whose contents were read and will be persisted."""

    relative_path: str
    size_bytes: int
    content: str


@dataclass(frozen=True)
class SkippedFile:
    """A file that was excluded from storage, and why."""

    relative_path: str
    size_bytes: int
    skip_reason: SkipReason


def exceeds_max_file_size(size_bytes: int, max_bytes: int) -> bool:
    """Return whether a single file's size is over the per-file limit."""
    return size_bytes > max_bytes


def looks_binary(sample: bytes) -> bool:
    """Return whether a byte sample looks like binary (non-text) content.

    Uses the same NUL-byte heuristic git itself uses: a text file should
    never contain a NUL byte within the first chunk of content. This has
    a known false-negative for binary formats that happen to avoid NUL
    in their first bytes, and a false-positive for UTF-16/32 encoded
    text — acceptable for a source-code scanner, not a general-purpose
    binary detector.
    """
    return b"\0" in sample[:_BINARY_SNIFF_SAMPLE_SIZE]
