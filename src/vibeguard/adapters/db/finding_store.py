"""Persistence operations for vulnerability scan findings."""

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from vibeguard.adapters.db.finding_model import FindingModel
from vibeguard.adapters.db.models import RepositoryFileModel
from vibeguard.core.finding import Finding


def list_stored_files_for_repository(
    session: Session, repository_id: int
) -> list[RepositoryFileModel]:
    """Fetch every successfully-stored (non-skipped) file for a repository."""
    statement = select(RepositoryFileModel).where(
        RepositoryFileModel.repository_id == repository_id,
        RepositoryFileModel.is_skipped.is_(False),
    )
    return list(session.execute(statement).scalars().all())


def get_repository_file_by_path(
    session: Session, repository_id: int, relative_path: str
) -> RepositoryFileModel | None:
    """Fetch one repository's file (stored or skipped) by its exact relative path.

    `relative_path` is matched exactly against the unique
    `(repository_id, relative_path)` constraint -- at most one row can
    ever match. Returns `None` if no file was recorded at that path
    during intake (never fetched fresh from GitHub).
    """
    statement = select(RepositoryFileModel).where(
        RepositoryFileModel.repository_id == repository_id,
        RepositoryFileModel.relative_path == relative_path,
    )
    return session.execute(statement).scalar_one_or_none()


def delete_findings_for_repository(session: Session, repository_id: int) -> None:
    """Delete every prior finding for a repository (rescans replace, not accumulate)."""
    session.execute(delete(FindingModel).where(FindingModel.repository_id == repository_id))


def insert_findings(session: Session, repository_id: int, findings: list[Finding]) -> None:
    """Persist every finding for a repository in one batch.

    A single bulk `INSERT` covering all rows, not a per-finding loop
    with per-row round trips (search-sort-efficiency).
    """
    if not findings:
        return
    rows = [
        {
            "repository_id": repository_id,
            "category": finding.category,
            "severity": finding.severity,
            "source": finding.source,
            "title": finding.title,
            "description": finding.description,
            "remediation": finding.remediation,
            "relative_path": finding.relative_path,
            "line_number": finding.line_number,
            "model": finding.model,
        }
        for finding in findings
    ]
    session.execute(insert(FindingModel), rows)


def list_findings_for_repository(session: Session, repository_id: int) -> list[FindingModel]:
    """Fetch every finding for a repository, worst-first.

    Ordered severity DESC (a native Postgres enum whose ascending
    declaration order is what makes DESC mean "worst first" — see
    `core/severity.py`), then path, then line, per search-sort-
    efficiency's explicit tie-break rule.
    """
    statement = (
        select(FindingModel)
        .where(FindingModel.repository_id == repository_id)
        .order_by(
            FindingModel.severity.desc(),
            FindingModel.relative_path.asc(),
            FindingModel.line_number.asc().nulls_last(),
        )
    )
    return list(session.execute(statement).scalars().all())
