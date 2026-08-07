"""Tests for user-submitted snippet finding fix persistence operations."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import (
    insert_snippet_findings,
    list_findings_for_snippet,
)
from vibeguard.adapters.db.snippet_fix_submission_model import SnippetFixSubmissionModel
from vibeguard.adapters.db.snippet_fix_submission_store import (
    get_fix_submission_by_finding_id,
    upsert_fix_submission,
)
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.core.vuln_category import VulnCategory


def _make_snippet(session: Session) -> SnippetModel:
    snippet = SnippetModel(
        content="x", filename="a.py", size_bytes=1, status=SnippetStatus.SCAN_PENDING
    )
    session.add(snippet)
    session.flush()
    return snippet


def _make_finding(session: Session, snippet: SnippetModel) -> SnippetFindingModel:
    finding = Finding(
        category=VulnCategory.INJECTION,
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


def test_get_fix_submission_by_finding_id_returns_none_when_none_exists(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    assert get_fix_submission_by_finding_id(db_session, finding.id) is None


def test_upsert_fix_submission_creates_when_none_exists(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    submission = upsert_fix_submission(db_session, finding.id, "fixed code")

    assert submission.id is not None
    assert submission.snippet_finding_id == finding.id
    assert submission.fixed_content == "fixed code"

    fetched = get_fix_submission_by_finding_id(db_session, finding.id)
    assert fetched is not None
    assert fetched.id == submission.id


def test_upsert_fix_submission_overwrites_an_existing_submission(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    first = upsert_fix_submission(db_session, finding.id, "first attempt")
    first_id = first.id

    second = upsert_fix_submission(db_session, finding.id, "second attempt")

    assert second.id == first_id
    fetched = get_fix_submission_by_finding_id(db_session, finding.id)
    assert fetched is not None
    assert fetched.fixed_content == "second attempt"


def test_upsert_fix_submission_does_not_create_a_second_row_on_resubmit(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)

    upsert_fix_submission(db_session, finding.id, "first attempt")
    upsert_fix_submission(db_session, finding.id, "second attempt")
    db_session.flush()

    rows = (
        db_session.query(SnippetFixSubmissionModel)
        .filter(SnippetFixSubmissionModel.snippet_finding_id == finding.id)
        .all()
    )
    assert len(rows) == 1
