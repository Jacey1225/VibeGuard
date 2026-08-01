"""Tests for remediation proposal and decision persistence operations."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vibeguard.adapters.db.finding_store import insert_findings, list_findings_for_repository
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.remediation_model import RemediationFindingModel
from vibeguard.adapters.db.remediation_store import (
    get_remediation_by_id,
    insert_remediation,
    list_remediations_for_repository,
    record_remediation_push_failure,
    record_remediation_push_success,
    record_remediation_rejection,
)
from vibeguard.adapters.db.user_store import upsert_user_from_github_login
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    session.add(repository)
    session.flush()
    return repository


def _make_finding_id(session: Session, repository_id: int, relative_path: str = "a.py") -> int:
    finding = Finding(
        category=VulnCategory.INJECTION,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path=relative_path,
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )
    insert_findings(session, repository_id, [finding])
    session.flush()
    return list_findings_for_repository(session, repository_id)[0].id


def _make_user_id(session: Session) -> int:
    user = upsert_user_from_github_login(
        session,
        github_user_id=1,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext",
        github_oauth_token_scope="public_repo",
    )
    return user.id


def _proposal(finding_ids: tuple[int, ...]) -> RemediationProposal:
    return RemediationProposal(
        relative_path="a.py",
        original_content="original",
        proposed_content="proposed",
        diff_text="--- a\n+++ b\n",
        summary="Parameterized the query.",
        model="test-model",
        finding_ids=finding_ids,
        introduces_new_heuristic_hits=False,
        new_heuristic_hit_summary=None,
    )


def test_insert_remediation_persists_fields_and_links_findings(db_session: Session):
    repository = _make_repository(db_session)
    finding_id = _make_finding_id(db_session, repository.id)

    remediation = insert_remediation(db_session, repository.id, _proposal((finding_id,)))

    assert remediation.id is not None
    assert remediation.status == RemediationStatus.PROPOSED
    assert remediation.relative_path == "a.py"
    links = (
        db_session.query(RemediationFindingModel)
        .filter_by(remediation_id=remediation.id)
        .all()
    )
    assert [link.finding_id for link in links] == [finding_id]


def test_insert_remediation_with_no_finding_ids_links_nothing(db_session: Session):
    repository = _make_repository(db_session)

    remediation = insert_remediation(db_session, repository.id, _proposal(()))

    links = (
        db_session.query(RemediationFindingModel)
        .filter_by(remediation_id=remediation.id)
        .all()
    )
    assert links == []


def test_get_remediation_by_id_returns_none_for_missing_row(db_session: Session):
    assert get_remediation_by_id(db_session, 999_999) is None


def test_list_remediations_for_repository_orders_newest_first(db_session: Session):
    repository = _make_repository(db_session)
    first = insert_remediation(db_session, repository.id, _proposal(()))
    second = insert_remediation(db_session, repository.id, _proposal(()))

    rows = list_remediations_for_repository(db_session, repository.id)

    assert [row.id for row in rows] == [second.id, first.id]


def test_record_remediation_rejection_sets_terminal_fields(db_session: Session):
    repository = _make_repository(db_session)
    user_id = _make_user_id(db_session)
    remediation = insert_remediation(db_session, repository.id, _proposal(()))
    decided_at = datetime.now(UTC)

    updated = record_remediation_rejection(
        db_session, remediation, user_id, decided_at, "not needed"
    )

    assert updated.status == RemediationStatus.REJECTED
    assert updated.decided_by_user_id == user_id
    assert updated.decision_reason == "not needed"


def test_record_remediation_push_success_sets_terminal_fields(db_session: Session):
    repository = _make_repository(db_session)
    user_id = _make_user_id(db_session)
    remediation = insert_remediation(db_session, repository.id, _proposal(()))
    decided_at = datetime.now(UTC)

    updated = record_remediation_push_success(
        db_session, remediation, user_id, decided_at, "main", "abc123"
    )

    assert updated.status == RemediationStatus.PUSHED
    assert updated.push_target_branch == "main"
    assert updated.pushed_commit_sha == "abc123"
    assert updated.push_failure_reason is None


def test_record_remediation_push_failure_sets_terminal_fields(db_session: Session):
    repository = _make_repository(db_session)
    user_id = _make_user_id(db_session)
    remediation = insert_remediation(db_session, repository.id, _proposal(()))
    decided_at = datetime.now(UTC)

    updated = record_remediation_push_failure(
        db_session,
        remediation,
        user_id,
        decided_at,
        "main",
        PushFailureReason.STALE_SHA_CONFLICT,
    )

    assert updated.status == RemediationStatus.PUSH_FAILED
    assert updated.push_failure_reason == PushFailureReason.STALE_SHA_CONFLICT


def test_record_remediation_push_failure_then_success_retries_cleanly(db_session: Session):
    repository = _make_repository(db_session)
    user_id = _make_user_id(db_session)
    remediation = insert_remediation(db_session, repository.id, _proposal(()))
    decided_at = datetime.now(UTC)

    record_remediation_push_failure(
        db_session,
        remediation,
        user_id,
        decided_at,
        "main",
        PushFailureReason.GITHUB_API_UNAVAILABLE,
    )
    retried = record_remediation_push_success(
        db_session, remediation, user_id, decided_at, "main", "def456"
    )

    assert retried.status == RemediationStatus.PUSHED
    assert retried.push_failure_reason is None
    assert retried.pushed_commit_sha == "def456"
