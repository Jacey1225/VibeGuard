"""Tests for the remediation approve/reject decision orchestration."""

from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

import vibeguard.engine.remediation_decision as remediation_decision_module
from vibeguard.adapters.auth.token_cipher import encrypt_token
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.remediation_store import insert_remediation
from vibeguard.adapters.db.user_store import upsert_user_from_github_login
from vibeguard.adapters.github.push_client import (
    GitHubPushConflictError,
    GitHubPushPermissionDeniedError,
    GitHubPushUnavailableError,
    PushedCommit,
)
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.engine.remediation_decision import (
    RemediationAlreadyDecidedError,
    RemediationNotFoundError,
    RemediationPushConflictError,
    RemediationPushPermissionDeniedError,
    RemediationPushUnavailableError,
    approve_remediation,
    reject_remediation,
)

_TEST_ENCRYPTION_KEY = SecretStr("lvk_pkjO7PGb7TsXVDj9B59YXFJTAI8nO_gyK1nGLd4=")


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(
        source_url="u", owner="octocat", name="Hello-World", status=RepositoryStatus.SCANNED
    )
    session.add(repository)
    session.flush()
    return repository


def _make_user(session: Session, *, scope: str = "public_repo"):
    ciphertext = encrypt_token("gho_realtoken123", _TEST_ENCRYPTION_KEY)
    return upsert_user_from_github_login(
        session,
        github_user_id=1,
        github_login="octocat",
        github_oauth_token_ciphertext=ciphertext,
        github_oauth_token_scope=scope,
    )


def _make_remediation(session: Session, repository: RepositoryModel, relative_path: str = "app.py"):
    proposal = RemediationProposal(
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
    return insert_remediation(session, repository.id, proposal)


def test_reject_remediation_missing_remediation_raises(db_session: Session):
    user = _make_user(db_session)
    with pytest.raises(RemediationNotFoundError):
        reject_remediation(999_999, user, None, db_session)


def test_reject_remediation_sets_rejected_status(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    updated = reject_remediation(remediation.id, user, "not needed", db_session)

    assert updated.status == RemediationStatus.REJECTED
    assert updated.decision_reason == "not needed"
    assert updated.decided_by_user_id == user.id


def test_reject_remediation_already_pushed_raises(db_session: Session):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)
    reject_remediation(remediation.id, user, None, db_session)

    with pytest.raises(RemediationAlreadyDecidedError):
        reject_remediation(remediation.id, user, None, db_session)


def test_approve_remediation_missing_remediation_raises(db_session: Session, settings_factory):
    user = _make_user(db_session)
    with pytest.raises(RemediationNotFoundError):
        approve_remediation(999_999, user, None, db_session, object(), settings_factory())


def test_approve_remediation_already_decided_raises(db_session: Session, settings_factory):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)
    reject_remediation(remediation.id, user, None, db_session)

    with pytest.raises(RemediationAlreadyDecidedError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())


def test_approve_remediation_insufficient_scope_raises_without_calling_github(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session, scope="read:user")

    fetch_branch_spy = Mock()
    monkeypatch.setattr(remediation_decision_module, "fetch_default_branch", fetch_branch_spy)

    with pytest.raises(RemediationPushPermissionDeniedError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    fetch_branch_spy.assert_not_called()
    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.GITHUB_PERMISSION_DENIED


def test_approve_remediation_happy_path_pushes_and_records_success(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(return_value=PushedCommit(commit_sha="commit1")),
    )

    updated = approve_remediation(
        remediation.id, user, None, db_session, object(), settings_factory()
    )

    assert updated.status == RemediationStatus.PUSHED
    assert updated.push_target_branch == "main"
    assert updated.pushed_commit_sha == "commit1"
    assert updated.decided_by_user_id == user.id


def test_approve_remediation_explicit_branch_skips_default_branch_fetch(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    fetch_branch_spy = Mock()
    monkeypatch.setattr(remediation_decision_module, "fetch_default_branch", fetch_branch_spy)
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(return_value=PushedCommit(commit_sha="commit1")),
    )

    updated = approve_remediation(
        remediation.id, user, "release-branch", db_session, object(), settings_factory()
    )

    fetch_branch_spy.assert_not_called()
    assert updated.push_target_branch == "release-branch"


def test_approve_remediation_conflict_sets_push_failed_and_raises(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(side_effect=GitHubPushConflictError("stale sha")),
    )

    with pytest.raises(RemediationPushConflictError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.STALE_SHA_CONFLICT


def test_approve_remediation_permission_denied_from_github_sets_push_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(side_effect=GitHubPushPermissionDeniedError("forbidden")),
    )

    with pytest.raises(RemediationPushPermissionDeniedError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.GITHUB_PERMISSION_DENIED


def test_approve_remediation_default_branch_permission_denied_sets_push_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module,
        "fetch_default_branch",
        Mock(side_effect=GitHubPushPermissionDeniedError("forbidden")),
    )

    with pytest.raises(RemediationPushPermissionDeniedError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.GITHUB_PERMISSION_DENIED
    assert remediation.push_target_branch is None


def test_approve_remediation_file_sha_unavailable_sets_push_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(
        remediation_decision_module,
        "fetch_file_sha",
        Mock(side_effect=GitHubPushUnavailableError("down")),
    )

    with pytest.raises(RemediationPushUnavailableError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.GITHUB_API_UNAVAILABLE
    assert remediation.push_target_branch == "main"


def test_approve_remediation_github_unavailable_sets_push_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module,
        "fetch_default_branch",
        Mock(side_effect=GitHubPushUnavailableError("down")),
    )

    with pytest.raises(RemediationPushUnavailableError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())

    assert remediation.status == RemediationStatus.PUSH_FAILED
    assert remediation.push_failure_reason == PushFailureReason.GITHUB_API_UNAVAILABLE


def test_approve_remediation_retry_after_failure_succeeds(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    remediation = _make_remediation(db_session, repository)
    user = _make_user(db_session)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(side_effect=GitHubPushConflictError("stale sha")),
    )
    with pytest.raises(RemediationPushConflictError):
        approve_remediation(remediation.id, user, None, db_session, object(), settings_factory())
    assert remediation.status == RemediationStatus.PUSH_FAILED

    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(return_value=PushedCommit(commit_sha="commit-retry")),
    )
    updated = approve_remediation(
        remediation.id, user, None, db_session, object(), settings_factory()
    )

    assert updated.status == RemediationStatus.PUSHED
    assert updated.pushed_commit_sha == "commit-retry"
    assert updated.push_failure_reason is None
