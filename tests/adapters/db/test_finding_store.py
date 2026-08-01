"""Tests for vulnerability finding persistence operations."""

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vibeguard.adapters.db.finding_store import (
    delete_findings_for_repository,
    insert_findings,
    list_findings_for_repository,
    list_stored_files_for_repository,
)
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    session.add(repository)
    session.flush()
    return repository


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


def test_list_stored_files_for_repository_excludes_skipped_files(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add_all(
        [
            RepositoryFileModel(
                repository_id=repository.id, relative_path="a.py", size_bytes=1, content="x"
            ),
            RepositoryFileModel(
                repository_id=repository.id,
                relative_path="big.bin",
                size_bytes=999,
                is_skipped=True,
                skip_reason="too_large",
            ),
        ]
    )
    db_session.flush()

    files = list_stored_files_for_repository(db_session, repository.id)

    assert len(files) == 1
    assert files[0].relative_path == "a.py"


def test_insert_findings_persists_all_fields(db_session: Session):
    repository = _make_repository(db_session)
    finding = _finding(severity=Severity.HIGH)

    insert_findings(db_session, repository.id, [finding])
    db_session.flush()

    rows = list_findings_for_repository(db_session, repository.id)
    assert len(rows) == 1
    assert rows[0].category == VulnCategory.INJECTION
    assert rows[0].severity == Severity.HIGH
    assert rows[0].model == "test-model"


def test_insert_findings_with_empty_list_is_a_no_op(db_session: Session):
    repository = _make_repository(db_session)
    insert_findings(db_session, repository.id, [])
    db_session.flush()
    assert list_findings_for_repository(db_session, repository.id) == []


def test_insert_findings_executes_a_single_round_trip(db_session: Session, db_engine: Engine):
    repository = _make_repository(db_session)
    findings = [_finding(severity=Severity.LOW, relative_path=f"f{i}.py") for i in range(30)]

    statement_count = 0

    def _count_statements(*args: object, **kwargs: object) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(db_engine, "before_cursor_execute", _count_statements)
    try:
        insert_findings(db_session, repository.id, findings)
    finally:
        event.remove(db_engine, "before_cursor_execute", _count_statements)

    assert statement_count == 1


def test_delete_findings_for_repository_removes_all_prior_findings(db_session: Session):
    repository = _make_repository(db_session)
    insert_findings(db_session, repository.id, [_finding(severity=Severity.LOW)])
    db_session.flush()
    assert len(list_findings_for_repository(db_session, repository.id)) == 1

    delete_findings_for_repository(db_session, repository.id)
    db_session.flush()

    assert list_findings_for_repository(db_session, repository.id) == []


def test_list_findings_for_repository_orders_worst_first(db_session: Session):
    # Deliberately inserted out of severity order, to catch a
    # regression in Severity's ascending declaration order (see
    # core/severity.py) -- this is the test most likely to catch a
    # real bug in the whole scan-engine feature.
    repository = _make_repository(db_session)
    insert_findings(
        db_session,
        repository.id,
        [
            _finding(severity=Severity.LOW, relative_path="b.py"),
            _finding(severity=Severity.CRITICAL, relative_path="c.py"),
            _finding(severity=Severity.MEDIUM, relative_path="a.py"),
            _finding(severity=Severity.INFO, relative_path="d.py"),
            _finding(severity=Severity.HIGH, relative_path="e.py"),
        ],
    )
    db_session.flush()

    rows = list_findings_for_repository(db_session, repository.id)

    assert [row.severity for row in rows] == [
        Severity.CRITICAL,
        Severity.HIGH,
        Severity.MEDIUM,
        Severity.LOW,
        Severity.INFO,
    ]


def test_list_findings_for_repository_breaks_severity_ties_by_path_then_line(
    db_session: Session,
):
    repository = _make_repository(db_session)
    insert_findings(
        db_session,
        repository.id,
        [
            _finding(severity=Severity.HIGH, relative_path="b.py", line_number=5),
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=10),
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=2),
            _finding(severity=Severity.HIGH, relative_path="a.py", line_number=None),
        ],
    )
    db_session.flush()

    rows = list_findings_for_repository(db_session, repository.id)

    assert [(row.relative_path, row.line_number) for row in rows] == [
        ("a.py", 2),
        ("a.py", 10),
        ("a.py", None),
        ("b.py", 5),
    ]
