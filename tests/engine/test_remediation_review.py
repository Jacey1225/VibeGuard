"""Tests for the remediation-review orchestration."""

import pytest
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.remediation_store import insert_remediation
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.engine.remediation_review import (
    RepositoryNotFoundError,
    get_remediations_for_repository,
)


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(
        source_url="u", owner="o", name="r", status=RepositoryStatus.SCANNED
    )
    session.add(repository)
    session.flush()
    return repository


def _proposal(relative_path: str) -> RemediationProposal:
    return RemediationProposal(
        relative_path=relative_path,
        original_content="original",
        proposed_content="proposed",
        diff_text="diff",
        summary="s",
        model="m",
        finding_ids=(),
        introduces_new_heuristic_hits=False,
        new_heuristic_hit_summary=None,
    )


def test_get_remediations_for_repository_missing_repository_raises(db_session: Session):
    with pytest.raises(RepositoryNotFoundError):
        get_remediations_for_repository(999_999, db_session)


def test_get_remediations_for_repository_returns_newest_first(db_session: Session):
    repository = _make_repository(db_session)
    first = insert_remediation(db_session, repository.id, _proposal("a.py"))
    second = insert_remediation(db_session, repository.id, _proposal("b.py"))

    rows = get_remediations_for_repository(repository.id, db_session)

    assert [row.id for row in rows] == [second.id, first.id]


def test_get_remediations_for_repository_with_none_returns_empty_list(db_session: Session):
    repository = _make_repository(db_session)
    assert get_remediations_for_repository(repository.id, db_session) == []
