"""Tests for remediation ORM model constraints against a real Postgres instance."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vibeguard.adapters.db.finding_store import insert_findings, list_findings_for_repository
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.remediation_model import RemediationFindingModel, RemediationModel
from vibeguard.adapters.db.user_model import UserModel
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    session.add(repository)
    session.flush()
    return repository


def _make_user(session: Session) -> UserModel:
    user = UserModel(
        github_user_id=1,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext",
        github_oauth_token_scope="public_repo",
    )
    session.add(user)
    session.flush()
    return user


def _make_finding_id(session: Session, repository: RepositoryModel) -> int:
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
    insert_findings(session, repository.id, [finding])
    session.flush()
    return list_findings_for_repository(session, repository.id)[0].id


def _base_remediation(repository_id: int, **overrides: object) -> RemediationModel:
    fields: dict[str, object] = {
        "repository_id": repository_id,
        "relative_path": "app.py",
        "original_content": "original",
        "proposed_content": "proposed",
        "diff_text": "diff",
        "summary": "s",
        "model": "m",
    }
    fields.update(overrides)
    return RemediationModel(**fields)


def test_remediation_model_persists_with_default_status(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(repository.id)
    db_session.add(remediation)
    db_session.flush()

    assert remediation.id is not None
    assert remediation.status == RemediationStatus.PROPOSED


def test_decided_at_required_once_decided_constraint(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(
        repository.id, status=RemediationStatus.REJECTED, decided_at=None
    )
    db_session.add(remediation)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_pushed_commit_sha_required_when_pushed_constraint(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(
        repository.id,
        status=RemediationStatus.PUSHED,
        decided_at=datetime.now(UTC),
        pushed_commit_sha=None,
    )
    db_session.add(remediation)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_push_failure_reason_required_when_push_failed_constraint(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(
        repository.id,
        status=RemediationStatus.PUSH_FAILED,
        decided_at=datetime.now(UTC),
        push_failure_reason=None,
    )
    db_session.add(remediation)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_remediation_with_all_required_decision_fields_persists(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(
        repository.id,
        status=RemediationStatus.PUSH_FAILED,
        decided_at=datetime.now(UTC),
        push_failure_reason=PushFailureReason.STALE_SHA_CONFLICT,
    )
    db_session.add(remediation)
    db_session.flush()
    assert remediation.id is not None


def test_remediation_cascades_on_repository_delete(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _base_remediation(repository.id)
    db_session.add(remediation)
    db_session.flush()

    remediation_id = remediation.id
    db_session.delete(repository)
    db_session.flush()

    db_session.expire_all()
    assert db_session.get(RemediationModel, remediation_id) is None


def test_remediation_decided_by_user_set_null_on_user_delete(db_session: Session):
    repository = _make_repository(db_session)
    user = _make_user(db_session)
    remediation = _base_remediation(
        repository.id,
        status=RemediationStatus.REJECTED,
        decided_at=datetime.now(UTC),
        decided_by_user_id=user.id,
    )
    db_session.add(remediation)
    db_session.flush()
    remediation_id = remediation.id

    db_session.delete(user)
    db_session.flush()

    db_session.expire_all()
    persisted = db_session.get(RemediationModel, remediation_id)
    assert persisted is not None
    assert persisted.decided_by_user_id is None


def test_remediation_findings_unique_pair_constraint(db_session: Session):
    repository = _make_repository(db_session)
    finding_id = _make_finding_id(db_session, repository)
    remediation = _base_remediation(repository.id)
    db_session.add(remediation)
    db_session.flush()

    db_session.add(
        RemediationFindingModel(remediation_id=remediation.id, finding_id=finding_id)
    )
    db_session.flush()
    db_session.add(
        RemediationFindingModel(remediation_id=remediation.id, finding_id=finding_id)
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_remediation_findings_cascades_on_remediation_delete(db_session: Session):
    repository = _make_repository(db_session)
    finding_id = _make_finding_id(db_session, repository)
    remediation = _base_remediation(repository.id)
    db_session.add(remediation)
    db_session.flush()

    link = RemediationFindingModel(remediation_id=remediation.id, finding_id=finding_id)
    db_session.add(link)
    db_session.flush()
    link_id = link.id

    db_session.delete(remediation)
    db_session.flush()

    db_session.expire_all()
    assert db_session.get(RemediationFindingModel, link_id) is None
