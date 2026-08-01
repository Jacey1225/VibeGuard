"""Lifecycle vocabulary for a proposed code fix."""

from enum import StrEnum


class RemediationStatus(StrEnum):
    """Where a proposed remediation currently stands.

    No standalone "approved" resting state — approval and the GitHub
    push are synchronous, matching the existing blocks-for-the-whole-
    request style of `/scan` and `POST /repositories`.
    """

    PROPOSED = "proposed"
    REJECTED = "rejected"
    PUSHED = "pushed"
    PUSH_FAILED = "push_failed"


class PushFailureReason(StrEnum):
    """Why a push attempt failed."""

    STALE_SHA_CONFLICT = "stale_sha_conflict"
    GITHUB_API_UNAVAILABLE = "github_api_unavailable"
    GITHUB_PERMISSION_DENIED = "github_permission_denied"
