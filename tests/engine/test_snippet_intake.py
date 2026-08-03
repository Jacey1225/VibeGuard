"""Tests for the plain-text snippet intake orchestration."""

from sqlalchemy.orm import Session

from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus
from vibeguard.engine.snippet_intake import DEFAULT_SNIPPET_FILENAME, run_snippet_intake


def test_run_snippet_intake_happy_path_marks_scan_pending(db_session: Session, settings_factory):
    snippet = run_snippet_intake("print('hi')", "app.py", db_session, settings_factory())

    assert snippet.status == SnippetStatus.SCAN_PENDING
    assert snippet.rejection_reason is None
    assert snippet.content == "print('hi')"
    assert snippet.filename == "app.py"
    assert snippet.size_bytes == len("print('hi')")


def test_run_snippet_intake_missing_filename_uses_the_default(
    db_session: Session, settings_factory
):
    snippet = run_snippet_intake("print('hi')", None, db_session, settings_factory())

    assert snippet.filename == DEFAULT_SNIPPET_FILENAME


def test_run_snippet_intake_blank_filename_uses_the_default(db_session: Session, settings_factory):
    snippet = run_snippet_intake("print('hi')", "   ", db_session, settings_factory())

    assert snippet.filename == DEFAULT_SNIPPET_FILENAME


def test_run_snippet_intake_empty_content_rejects(db_session: Session, settings_factory):
    snippet = run_snippet_intake("", "app.py", db_session, settings_factory())

    assert snippet.status == SnippetStatus.REJECTED
    assert snippet.rejection_reason == SnippetRejectionReason.EMPTY_CONTENT


def test_run_snippet_intake_whitespace_only_content_rejects(db_session: Session, settings_factory):
    snippet = run_snippet_intake("   \n\t  ", "app.py", db_session, settings_factory())

    assert snippet.status == SnippetStatus.REJECTED
    assert snippet.rejection_reason == SnippetRejectionReason.EMPTY_CONTENT


def test_run_snippet_intake_oversized_content_rejects_without_storing_it(
    db_session: Session, settings_factory
):
    settings = settings_factory(max_file_size_bytes=10)

    snippet = run_snippet_intake("x" * 50, "app.py", db_session, settings)

    assert snippet.status == SnippetStatus.REJECTED
    assert snippet.rejection_reason == SnippetRejectionReason.TOO_LARGE
    assert snippet.content == ""
    assert snippet.size_bytes == 50
