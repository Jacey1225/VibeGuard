"""Orchestrating a human reviewer's approve/reject decision on a remediation.

The highest-risk code in this feature: approval triggers an
irreversible push to a real GitHub branch. GitHub's own conflict signal
(a 409 on the write) is the final authority — this module never
attempts an automatic merge on that signal, and always re-fetches the
target branch and file sha fresh immediately before writing rather than
trusting anything cached from proposal time.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy.orm import Session

from vibeguard.adapters.auth.token_cipher import decrypt_token
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.remediation_model import RemediationModel
from vibeguard.adapters.db.remediation_store import (
    get_remediation_by_id,
    record_remediation_push_failure,
    record_remediation_push_success,
    record_remediation_rejection,
)
from vibeguard.adapters.db.repository_store import get_repository_by_id
from vibeguard.adapters.db.user_model import UserModel
from vibeguard.adapters.github.push_client import (
    GitHubPushConflictError,
    GitHubPushPermissionDeniedError,
    GitHubPushUnavailableError,
    fetch_default_branch,
    fetch_file_sha,
    push_file_update,
)
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus

_REQUIRED_PUSH_SCOPE = "public_repo"
_RETRYABLE_STATUSES = frozenset({RemediationStatus.PROPOSED, RemediationStatus.PUSH_FAILED})


class RemediationNotFoundError(RuntimeError):
    """Raised when a remediation id doesn't exist."""


class RemediationAlreadyDecidedError(RuntimeError):
    """Raised when a remediation has already reached a terminal decision (pushed/rejected)."""


class RemediationPushConflictError(RuntimeError):
    """Raised when the target file changed upstream since this proposal was based on it."""


class RemediationPushUnavailableError(RuntimeError):
    """Raised when GitHub's API can't be reached or fails unexpectedly during a push."""


class RemediationPushPermissionDeniedError(RuntimeError):
    """Raised when the approving user's token can't write to the target repository."""


def reject_remediation(
    remediation_id: int, deciding_user: UserModel, decision_reason: str | None, session: Session
) -> RemediationModel:
    """Reject a proposed or previously-failed remediation.

    Raises:
        RemediationNotFoundError: no remediation with this id exists.
        RemediationAlreadyDecidedError: already `pushed` or `rejected`.
    """
    remediation = _get_decidable_remediation(remediation_id, session)
    return record_remediation_rejection(
        session, remediation, deciding_user.id, datetime.now(UTC), decision_reason
    )


def approve_remediation(
    remediation_id: int,
    approving_user: UserModel,
    target_branch_override: str | None,
    session: Session,
    github_client: httpx.Client,
    settings: Settings,
) -> RemediationModel:
    """Approve a remediation and push it to the target GitHub repository.

    Uses the *approving* user's own stored token, never the original
    intake submitter's — deliberate, since the person clicking approve
    is the one taking responsibility for the push. Re-approving a prior
    `push_failed` remediation retries from scratch with fresh branch
    and file-sha fetches; `pushed`/`rejected` are terminal.

    Raises:
        RemediationNotFoundError: no remediation with this id exists.
        RemediationAlreadyDecidedError: already `pushed` or `rejected`.
        RemediationPushPermissionDeniedError: the approving user's
            token lacks `public_repo` scope, or GitHub reports a
            permission failure.
        RemediationPushConflictError: the target file changed upstream
            since this proposal was generated.
        RemediationPushUnavailableError: GitHub's API couldn't be
            reached or failed unexpectedly.
    """
    remediation = _get_decidable_remediation(remediation_id, session)
    repository = get_repository_by_id(session, remediation.repository_id)
    if repository is None:
        # The FK to repositories makes this unreachable in practice; guarded
        # explicitly rather than trusted, since it's a real caller-visible
        # invariant, not a test assertion.
        raise RuntimeError(
            f"remediation {remediation.id} references missing "
            f"repository {remediation.repository_id}"
        )

    access_token = _decrypt_and_verify_scope(
        session, remediation, approving_user, settings, datetime.now(UTC)
    )

    try:
        branch = target_branch_override or fetch_default_branch(
            repository.owner,
            repository.name,
            access_token,
            github_client,
            settings.github_api_timeout_seconds,
        )
    except GitHubPushPermissionDeniedError as error:
        _record_push_failure(
            session,
            remediation,
            approving_user.id,
            None,
            PushFailureReason.GITHUB_PERMISSION_DENIED,
        )
        raise RemediationPushPermissionDeniedError(str(error)) from error
    except GitHubPushUnavailableError as error:
        _record_push_failure(
            session, remediation, approving_user.id, None, PushFailureReason.GITHUB_API_UNAVAILABLE
        )
        raise RemediationPushUnavailableError(str(error)) from error

    try:
        sha = fetch_file_sha(
            repository.owner,
            repository.name,
            remediation.relative_path,
            branch,
            access_token,
            github_client,
            settings.github_api_timeout_seconds,
        )
        pushed = push_file_update(
            repository.owner,
            repository.name,
            remediation.relative_path,
            branch,
            remediation.proposed_content,
            sha,
            f"VibeGuard: automated fix for {remediation.relative_path}",
            access_token,
            github_client,
            settings.github_api_timeout_seconds,
        )
    except GitHubPushConflictError as error:
        _record_push_failure(
            session, remediation, approving_user.id, branch, PushFailureReason.STALE_SHA_CONFLICT
        )
        raise RemediationPushConflictError(str(error)) from error
    except GitHubPushPermissionDeniedError as error:
        _record_push_failure(
            session,
            remediation,
            approving_user.id,
            branch,
            PushFailureReason.GITHUB_PERMISSION_DENIED,
        )
        raise RemediationPushPermissionDeniedError(str(error)) from error
    except GitHubPushUnavailableError as error:
        _record_push_failure(
            session,
            remediation,
            approving_user.id,
            branch,
            PushFailureReason.GITHUB_API_UNAVAILABLE,
        )
        raise RemediationPushUnavailableError(str(error)) from error

    return record_remediation_push_success(
        session, remediation, approving_user.id, datetime.now(UTC), branch, pushed.commit_sha
    )


def _record_push_failure(
    session: Session,
    remediation: RemediationModel,
    approving_user_id: int,
    branch: str | None,
    reason: PushFailureReason,
) -> None:
    record_remediation_push_failure(
        session, remediation, approving_user_id, datetime.now(UTC), branch, reason
    )


def _get_decidable_remediation(remediation_id: int, session: Session) -> RemediationModel:
    remediation = get_remediation_by_id(session, remediation_id)
    if remediation is None:
        raise RemediationNotFoundError(f"no remediation with id {remediation_id}")
    if remediation.status not in _RETRYABLE_STATUSES:
        raise RemediationAlreadyDecidedError(
            f"remediation {remediation_id} already has status {remediation.status.value}"
        )
    return remediation


def _decrypt_and_verify_scope(
    session: Session,
    remediation: RemediationModel,
    approving_user: UserModel,
    settings: Settings,
    decided_at: datetime,
) -> str:
    """Decrypt the approving user's token and verify it before any GitHub call fires."""
    granted_scopes = {
        scope.strip() for scope in approving_user.github_oauth_token_scope.split(",")
    }
    if _REQUIRED_PUSH_SCOPE not in granted_scopes:
        record_remediation_push_failure(
            session,
            remediation,
            approving_user.id,
            decided_at,
            None,
            PushFailureReason.GITHUB_PERMISSION_DENIED,
        )
        raise RemediationPushPermissionDeniedError(
            "the approving user's token doesn't have public_repo scope"
        )
    return decrypt_token(
        approving_user.github_oauth_token_ciphertext, settings.token_encryption_key
    )
