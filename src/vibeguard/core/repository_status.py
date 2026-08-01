"""Lifecycle vocabulary for a repository intake attempt."""

from enum import StrEnum


class RepositoryStatus(StrEnum):
    """Where a repository intake attempt currently stands."""

    PENDING = "pending"
    CLONING = "cloning"
    STORING = "storing"
    SCAN_PENDING_IMPLEMENTATION = "scan_pending_implementation"
    SCANNING = "scanning"
    SCANNED = "scanned"
    SCAN_FAILED = "scan_failed"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    """Why an intake attempt was rejected before or during cloning."""

    NOT_PUBLIC_OR_NOT_FOUND = "not_public_or_not_found"
    REPO_TOO_LARGE = "repo_too_large"
    CLONE_FAILED = "clone_failed"
    CLONE_TIMEOUT = "clone_timeout"


class ScanFailureReason(StrEnum):
    """Why a vulnerability scan failed outright (not merely incomplete)."""

    LLM_UNAVAILABLE = "llm_unavailable"


class SkipReason(StrEnum):
    """Why one file within an otherwise-stored repository was skipped."""

    TOO_LARGE = "too_large"
    BINARY = "binary"
    FILE_COUNT_LIMIT_EXCEEDED = "file_count_limit_exceeded"
    TOTAL_SIZE_LIMIT_EXCEEDED = "total_size_limit_exceeded"
    UNSAFE_PATH = "unsafe_path"
