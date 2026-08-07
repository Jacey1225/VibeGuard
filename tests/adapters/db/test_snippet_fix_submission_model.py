"""Tests for the SnippetFixSubmission ORM model's constraints, against a real Postgres instance."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import (
    insert_snippet_findings,
    list_findings_for_snippet,
)
from vibeguard.adapters.db.snippet_fix_submission_model import SnippetFixSubmissionModel
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.core.vuln_category import VulnCategory


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


def test_snippet_fix_submission_persists_with_expected_fields(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    submission = SnippetFixSubmissionModel(
        snippet_finding_id=finding.id, fixed_content='password = get_secret("admin_password")'
    )
    db_session.add(submission)
    db_session.flush()

    assert submission.id is not None
    assert submission.fixed_content == 'password = get_secret("admin_password")'
    assert submission.created_at is not None


def test_snippet_fix_submission_unique_per_finding_constraint(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    db_session.add(
        SnippetFixSubmissionModel(snippet_finding_id=finding.id, fixed_content="fix one")
    )
    db_session.flush()

    db_session.add(
        SnippetFixSubmissionModel(snippet_finding_id=finding.id, fixed_content="fix two")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_snippet_fix_submission_cascades_on_finding_delete(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    submission = SnippetFixSubmissionModel(snippet_finding_id=finding.id, fixed_content="fix")
    db_session.add(submission)
    db_session.flush()
    submission_id = submission.id

    db_session.delete(finding)
    db_session.flush()

    db_session.expire_all()
    assert db_session.get(SnippetFixSubmissionModel, submission_id) is None
