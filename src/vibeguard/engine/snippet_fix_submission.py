"""Submitting and reading a user-authored fix for one snippet finding.

The plain-text counterpart to the repository remediation feature, but
deliberately much thinner: no LLM call, no approve/reject/push
lifecycle, no `get_current_user` dependency anywhere in this module.
The user pastes their own already-fixed code; it's validated the same
way `engine/snippet_intake.py` validates a submitted snippet (non-empty,
within the shared per-file size budget) and stored as-is.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import get_snippet_finding_by_id
from vibeguard.adapters.db.snippet_fix_submission_model import SnippetFixSubmissionModel
from vibeguard.adapters.db.snippet_fix_submission_store import (
    get_fix_submission_by_finding_id,
    upsert_fix_submission,
)
from vibeguard.adapters.db.snippet_store import get_snippet_by_id
from vibeguard.core.file_filter import exceeds_max_file_size
from vibeguard.engine.snippet_scan import SnippetNotFoundError


class SnippetFindingNotFoundError(RuntimeError):
    """Raised when a finding id doesn't exist, or doesn't belong to the given snippet."""


class SnippetFixSubmissionNotFoundError(RuntimeError):
    """Raised when a finding exists but has no fix submitted for it yet."""


class SnippetFixContentInvalidError(RuntimeError):
    """Raised when submitted fix content is empty or over the size budget."""


def submit_snippet_fix(
    snippet_id: int,
    finding_id: int,
    fixed_content: str,
    session: Session,
    settings: Settings,
) -> SnippetFixSubmissionModel:
    """Validate and store a user-authored fix for one finding.

    Resubmitting for the same finding overwrites the prior submission --
    there's no reviewer other than the submitter and nothing to
    reconcile, so "exists or doesn't" is sufficient for v1.

    Raises:
        SnippetNotFoundError: no snippet with this id exists.
        SnippetFindingNotFoundError: no finding with this id exists for
            this snippet.
        SnippetFixContentInvalidError: `fixed_content` is empty (after
            stripping whitespace) or exceeds `settings.max_file_size_bytes`
            -- the same per-file budget snippet intake enforces.
    """
    finding = _get_finding_for_snippet(snippet_id, finding_id, session)
    _validate_fix_content(fixed_content, settings)
    return upsert_fix_submission(session, finding.id, fixed_content)


def get_snippet_fix(
    snippet_id: int, finding_id: int, session: Session
) -> SnippetFixSubmissionModel:
    """Look up the fix submitted for one finding.

    Raises:
        SnippetNotFoundError: no snippet with this id exists.
        SnippetFindingNotFoundError: no finding with this id exists for
            this snippet.
        SnippetFixSubmissionNotFoundError: the finding exists but no fix
            has been submitted for it yet.
    """
    finding = _get_finding_for_snippet(snippet_id, finding_id, session)
    submission = get_fix_submission_by_finding_id(session, finding.id)
    if submission is None:
        raise SnippetFixSubmissionNotFoundError(
            f"no fix submitted yet for snippet finding {finding_id}"
        )
    return submission


def _get_finding_for_snippet(
    snippet_id: int, finding_id: int, session: Session
) -> SnippetFindingModel:
    if get_snippet_by_id(session, snippet_id) is None:
        raise SnippetNotFoundError(f"no snippet with id {snippet_id}")

    finding = get_snippet_finding_by_id(session, finding_id)
    if finding is None or finding.snippet_id != snippet_id:
        raise SnippetFindingNotFoundError(
            f"no finding with id {finding_id} for snippet {snippet_id}"
        )
    return finding


def _validate_fix_content(fixed_content: str, settings: Settings) -> None:
    if not fixed_content.strip():
        raise SnippetFixContentInvalidError("fixed_content must not be empty")

    size_bytes = len(fixed_content.encode("utf-8"))
    if exceeds_max_file_size(size_bytes, settings.max_file_size_bytes):
        raise SnippetFixContentInvalidError(
            f"fixed_content exceeds the {settings.max_file_size_bytes}-byte size budget"
        )
