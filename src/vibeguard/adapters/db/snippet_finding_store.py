"""Persistence operations for plain-text snippet scan findings."""

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.core.finding import Finding


def get_snippet_finding_by_id(
    session: Session, snippet_finding_id: int
) -> SnippetFindingModel | None:
    """Fetch one snippet finding by id, or `None` if it doesn't exist."""
    return session.get(SnippetFindingModel, snippet_finding_id)


def delete_findings_for_snippet(session: Session, snippet_id: int) -> None:
    """Delete every prior finding for a snippet (rescans replace, not accumulate)."""
    session.execute(delete(SnippetFindingModel).where(SnippetFindingModel.snippet_id == snippet_id))


def insert_snippet_findings(session: Session, snippet_id: int, findings: list[Finding]) -> None:
    """Persist every finding for a snippet in one batch.

    A single bulk `INSERT` covering all rows, not a per-finding loop
    with per-row round trips (search-sort-efficiency).
    """
    if not findings:
        return
    rows = [
        {
            "snippet_id": snippet_id,
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
    session.execute(insert(SnippetFindingModel), rows)


def list_findings_for_snippet(session: Session, snippet_id: int) -> list[SnippetFindingModel]:
    """Fetch every finding for a snippet, worst-first.

    Ordered severity DESC (a native Postgres enum whose ascending
    declaration order is what makes DESC mean "worst first" -- see
    `core/severity.py`), then path, then line, per search-sort-
    efficiency's explicit tie-break rule -- the same ordering rule
    `finding_store.list_findings_for_repository` uses.
    """
    statement = (
        select(SnippetFindingModel)
        .where(SnippetFindingModel.snippet_id == snippet_id)
        .order_by(
            SnippetFindingModel.severity.desc(),
            SnippetFindingModel.relative_path.asc(),
            SnippetFindingModel.line_number.asc().nulls_last(),
        )
    )
    return list(session.execute(statement).scalars().all())
