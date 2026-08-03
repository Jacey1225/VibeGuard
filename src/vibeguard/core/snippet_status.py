"""Lifecycle vocabulary for a plain-text code snippet scan attempt."""

from enum import StrEnum


class SnippetStatus(StrEnum):
    """Where a plain-text snippet submission currently stands.

    Deliberately smaller than `RepositoryStatus`: a snippet has no
    clone/storage phase, so there's no `CLONING`/`STORING` equivalent.
    """

    PENDING = "pending"
    SCAN_PENDING = "scan_pending"
    SCANNING = "scanning"
    SCANNED = "scanned"
    SCAN_FAILED = "scan_failed"
    REJECTED = "rejected"


class SnippetRejectionReason(StrEnum):
    """Why a submitted snippet was rejected before ever being scanned."""

    EMPTY_CONTENT = "empty_content"
    TOO_LARGE = "too_large"
