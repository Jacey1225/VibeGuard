"""Tests for submitting and reading a user-authored fix for a snippet finding."""

import pytest
from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import (
    insert_snippet_findings,
    list_findings_for_snippet,
)
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.snippet_fix_submission import (
    SnippetFindingNotFoundError,
    SnippetFixContentInvalidError,
    SnippetFixSubmissionNotFoundError,
    get_snippet_fix,
    submit_snippet_fix,
)
from vibeguard.engine.snippet_scan import SnippetNotFoundError


def _make_snippet(session: Session, content: str = 'password = "admin"') -> SnippetModel:
    snippet = SnippetModel(
        content=content, filename="a.py", size_bytes=len(content), status=SnippetStatus.SCAN_PENDING
    )
    session.add(snippet)
    session.flush()
    return snippet


def _make_finding(session: Session, snippet: SnippetModel) -> SnippetFindingModel:
    finding = Finding(
        category=VulnCategory.SECURITY_MISCONFIGURATION,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path="a.py",
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )
    insert_snippet_findings(session, snippet.id, [finding])
    session.flush()
    return list_findings_for_snippet(session, snippet.id)[0]


def test_submit_snippet_fix_happy_path_persists_and_returns_submission(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    settings = settings_factory()
    submission = submit_snippet_fix(
        snippet.id, finding.id, 'password = get_secret("admin_password")', db_session, settings
    )

    assert submission.snippet_finding_id == finding.id
    assert submission.fixed_content == 'password = get_secret("admin_password")'


def test_submit_snippet_fix_unknown_snippet_raises_snippet_not_found(
    db_session: Session, settings_factory
):
    with pytest.raises(SnippetNotFoundError):
        submit_snippet_fix(999999, 1, "fix", db_session, settings_factory())


def test_submit_snippet_fix_unknown_finding_raises_finding_not_found(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)

    with pytest.raises(SnippetFindingNotFoundError):
        submit_snippet_fix(snippet.id, 999999, "fix", db_session, settings_factory())


def test_submit_snippet_fix_finding_belongs_to_a_different_snippet_raises_finding_not_found(
    db_session: Session, settings_factory
):
    snippet_a = _make_snippet(db_session)
    snippet_b = _make_snippet(db_session, content="other content")
    finding_on_b = _make_finding(db_session, snippet_b)

    # finding_on_b is real, but scoped to snippet_b -- attempting to attach
    # a fix to it via snippet_a's id must not succeed just because the
    # finding id exists somewhere in the table.
    with pytest.raises(SnippetFindingNotFoundError):
        submit_snippet_fix(snippet_a.id, finding_on_b.id, "fix", db_session, settings_factory())


def test_submit_snippet_fix_empty_content_raises_content_invalid(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    with pytest.raises(SnippetFixContentInvalidError):
        submit_snippet_fix(snippet.id, finding.id, "   ", db_session, settings_factory())


def test_submit_snippet_fix_over_budget_content_raises_content_invalid(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    settings = settings_factory(max_file_size_bytes=10)

    with pytest.raises(SnippetFixContentInvalidError):
        submit_snippet_fix(snippet.id, finding.id, "x" * 50, db_session, settings)


def test_submit_snippet_fix_resubmit_overwrites_prior_submission(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    settings = settings_factory()

    first = submit_snippet_fix(snippet.id, finding.id, "first attempt", db_session, settings)
    second = submit_snippet_fix(snippet.id, finding.id, "second attempt", db_session, settings)

    assert second.id == first.id
    fetched = get_snippet_fix(snippet.id, finding.id, db_session)
    assert fetched.fixed_content == "second attempt"


def test_get_snippet_fix_happy_path_returns_submission(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    settings = settings_factory()
    submit_snippet_fix(snippet.id, finding.id, "the fix", db_session, settings)

    fetched = get_snippet_fix(snippet.id, finding.id, db_session)

    assert fetched.fixed_content == "the fix"


def test_get_snippet_fix_unknown_snippet_raises_snippet_not_found(
    db_session: Session, settings_factory
):
    with pytest.raises(SnippetNotFoundError):
        get_snippet_fix(999999, 1, db_session)


def test_get_snippet_fix_unknown_finding_raises_finding_not_found(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)

    with pytest.raises(SnippetFindingNotFoundError):
        get_snippet_fix(snippet.id, 999999, db_session)


def test_get_snippet_fix_no_submission_yet_raises_submission_not_found(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    with pytest.raises(SnippetFixSubmissionNotFoundError):
        get_snippet_fix(snippet.id, finding.id, db_session)
