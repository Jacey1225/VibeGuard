"""Tests for snippet intake persistence operations."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_store import (
    insert_snippet,
    update_snippet_scan_outcome,
    update_snippet_status,
)
from vibeguard.core.repository_status import ScanFailureReason
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus


def test_insert_snippet_creates_a_row_with_the_given_status(db_session: Session):
    snippet = insert_snippet(db_session, "print(1)", "a.py", 8, SnippetStatus.SCAN_PENDING, None)

    assert snippet.id is not None
    assert snippet.content == "print(1)"
    assert snippet.filename == "a.py"
    assert snippet.size_bytes == 8
    assert snippet.status == SnippetStatus.SCAN_PENDING
    assert snippet.rejection_reason is None


def test_insert_snippet_persists_a_rejection_reason(db_session: Session):
    snippet = insert_snippet(
        db_session, "", "a.py", 0, SnippetStatus.REJECTED, SnippetRejectionReason.EMPTY_CONTENT
    )

    assert snippet.status == SnippetStatus.REJECTED
    assert snippet.rejection_reason == SnippetRejectionReason.EMPTY_CONTENT


def test_update_snippet_status_sets_the_new_status(db_session: Session):
    snippet = insert_snippet(db_session, "x", "a.py", 1, SnippetStatus.SCAN_PENDING, None)

    updated = update_snippet_status(db_session, snippet, SnippetStatus.SCANNING)

    assert updated.status == SnippetStatus.SCANNING


def test_update_snippet_scan_outcome_writes_completion_fields(db_session: Session):
    snippet = insert_snippet(db_session, "x", "a.py", 1, SnippetStatus.SCAN_PENDING, None)

    updated = update_snippet_scan_outcome(
        db_session,
        snippet,
        status=SnippetStatus.SCAN_FAILED,
        scan_incomplete=False,
        scan_incomplete_reason=None,
        scan_failure_reason=ScanFailureReason.LLM_UNAVAILABLE,
    )

    assert updated.status == SnippetStatus.SCAN_FAILED
    assert updated.scan_incomplete is False
    assert updated.scan_failure_reason == ScanFailureReason.LLM_UNAVAILABLE
