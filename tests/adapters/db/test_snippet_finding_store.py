"""Tests for plain-text snippet scan finding persistence operations."""

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_finding_store import (
    delete_findings_for_snippet,
    insert_snippet_findings,
    list_findings_for_snippet,
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


def _finding(
    *, severity: Severity, relative_path: str = "a.py", line_number: int | None = 1
) -> Finding:
    return Finding(
        category=VulnCategory.INJECTION,
        severity=severity,
        title="t",
        description="d",
        remediation="r",
        relative_path=relative_path,
        line_number=line_number,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )


def test_insert_snippet_findings_persists_all_fields(db_session: Session):
    snippet = _make_snippet(db_session)
    finding = _finding(severity=Severity.HIGH)

    insert_snippet_findings(db_session, snippet.id, [finding])
    db_session.flush()

    rows = list_findings_for_snippet(db_session, snippet.id)
    assert len(rows) == 1
    assert rows[0].category == VulnCategory.INJECTION
    assert rows[0].severity == Severity.HIGH
    assert rows[0].model == "test-model"


def test_insert_snippet_findings_with_empty_list_is_a_no_op(db_session: Session):
    snippet = _make_snippet(db_session)
    insert_snippet_findings(db_session, snippet.id, [])
    db_session.flush()
    assert list_findings_for_snippet(db_session, snippet.id) == []


def test_insert_snippet_findings_executes_a_single_round_trip(
    db_session: Session, db_engine: Engine
):
    snippet = _make_snippet(db_session)
    findings = [_finding(severity=Severity.LOW, relative_path=f"f{i}.py") for i in range(30)]

    statement_count = 0

    def _count_statements(*args: object, **kwargs: object) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(db_engine, "before_cursor_execute", _count_statements)
    try:
        insert_snippet_findings(db_session, snippet.id, findings)
    finally:
        event.remove(db_engine, "before_cursor_execute", _count_statements)

    assert statement_count == 1


def test_delete_findings_for_snippet_removes_all_prior_findings(db_session: Session):
    snippet = _make_snippet(db_session)
    insert_snippet_findings(db_session, snippet.id, [_finding(severity=Severity.LOW)])
    db_session.flush()
    assert len(list_findings_for_snippet(db_session, snippet.id)) == 1

    delete_findings_for_snippet(db_session, snippet.id)
    db_session.flush()

    assert list_findings_for_snippet(db_session, snippet.id) == []


def test_list_findings_for_snippet_orders_worst_first(db_session: Session):
    snippet = _make_snippet(db_session)
    insert_snippet_findings(
        db_session,
        snippet.id,
        [
            _finding(severity=Severity.LOW, relative_path="b.py"),
            _finding(severity=Severity.CRITICAL, relative_path="c.py"),
            _finding(severity=Severity.MEDIUM, relative_path="a.py"),
        ],
    )
    db_session.flush()

    rows = list_findings_for_snippet(db_session, snippet.id)

    assert [row.severity for row in rows] == [Severity.CRITICAL, Severity.MEDIUM, Severity.LOW]


def test_list_findings_for_snippet_breaks_severity_ties_by_path_then_line(db_session: Session):
    snippet = _make_snippet(db_session)
    insert_snippet_findings(
        db_session,
        snippet.id,
        [
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=10),
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=2),
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=None),
        ],
    )
    db_session.flush()

    rows = list_findings_for_snippet(db_session, snippet.id)

    assert [row.line_number for row in rows] == [2, 10, None]
