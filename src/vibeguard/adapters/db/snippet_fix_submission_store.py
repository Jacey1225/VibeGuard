"""Persistence operations for user-submitted snippet finding fixes."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_fix_submission_model import SnippetFixSubmissionModel


def get_fix_submission_by_finding_id(
    session: Session, snippet_finding_id: int
) -> SnippetFixSubmissionModel | None:
    """Fetch the fix submitted for one finding, or `None` if none exists yet.

    A single indexed lookup on `snippet_finding_id`'s unique constraint,
    not a scan.
    """
    return (
        session.query(SnippetFixSubmissionModel)
        .filter(SnippetFixSubmissionModel.snippet_finding_id == snippet_finding_id)
        .one_or_none()
    )


def upsert_fix_submission(
    session: Session, snippet_finding_id: int, fixed_content: str
) -> SnippetFixSubmissionModel:
    """Create a finding's fix submission, or overwrite it if one already exists.

    One submission per finding is the v1 rule -- resubmitting overwrites
    rather than erroring, since there's no reviewer other than the
    submitter and nothing to reconcile.
    """
    existing = get_fix_submission_by_finding_id(session, snippet_finding_id)
    if existing is not None:
        existing.fixed_content = fixed_content
        session.flush()
        return existing

    submission = SnippetFixSubmissionModel(
        snippet_finding_id=snippet_finding_id, fixed_content=fixed_content
    )
    session.add(submission)
    session.flush()
    return submission
