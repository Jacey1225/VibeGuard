"""Persistence operations for plain-text snippet scan attempts."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.core.repository_status import ScanFailureReason
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus


def get_snippet_by_id(session: Session, snippet_id: int) -> SnippetModel | None:
    """Fetch a snippet by id, or `None` if it doesn't exist."""
    return session.get(SnippetModel, snippet_id)


def insert_snippet(
    session: Session,
    content: str,
    filename: str,
    size_bytes: int,
    status: SnippetStatus,
    rejection_reason: SnippetRejectionReason | None,
) -> SnippetModel:
    """Create and persist a new snippet submission row."""
    snippet = SnippetModel(
        content=content,
        filename=filename,
        size_bytes=size_bytes,
        status=status,
        rejection_reason=rejection_reason,
    )
    session.add(snippet)
    session.flush()
    return snippet


def update_snippet_status(
    session: Session, snippet: SnippetModel, status: SnippetStatus
) -> SnippetModel:
    """Update a snippet's status."""
    snippet.status = status
    session.flush()
    return snippet


def update_snippet_scan_outcome(
    session: Session,
    snippet: SnippetModel,
    status: SnippetStatus,
    scan_incomplete: bool,
    scan_incomplete_reason: str | None,
    scan_failure_reason: ScanFailureReason | None,
) -> SnippetModel:
    """Finalize a snippet scan's outcome: status, incompleteness, and failure reason."""
    snippet.status = status
    snippet.scan_incomplete = scan_incomplete
    snippet.scan_incomplete_reason = scan_incomplete_reason
    snippet.scan_failure_reason = scan_failure_reason
    session.flush()
    return snippet
