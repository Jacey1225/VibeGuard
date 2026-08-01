"""Tests for the remediation generation/review/approve/reject routes."""

from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

import vibeguard.engine.remediation_decision as remediation_decision_module
import vibeguard.engine.remediation_generation as remediation_generation_module
from vibeguard.adapters.auth.token_cipher import encrypt_token
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.finding_store import insert_findings
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.adapters.db.remediation_store import get_remediation_by_id, insert_remediation
from vibeguard.adapters.db.user_model import UserModel
from vibeguard.adapters.db.user_store import upsert_user_from_github_login
from vibeguard.adapters.github.push_client import GitHubPushConflictError, PushedCommit
from vibeguard.adapters.llm.remediation_client import GeneratedRemediation
from vibeguard.api.auth_dependencies import UnauthenticatedError, get_current_user
from vibeguard.api.dependencies import (
    get_db_session,
    get_github_client,
    get_llm_client,
    get_settings,
)
from vibeguard.api.error_handlers import (
    handle_remediation_already_decided,
    handle_remediation_not_found,
    handle_remediation_push_conflict,
    handle_remediation_push_permission_denied,
    handle_remediation_push_unavailable,
    handle_repository_not_found,
    handle_repository_not_ready_for_remediation,
    handle_unauthenticated,
)
from vibeguard.api.routes.remediations import router
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.remediation_status import RemediationStatus
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.remediation_decision import (
    RemediationAlreadyDecidedError,
    RemediationNotFoundError,
    RemediationPushConflictError,
    RemediationPushPermissionDeniedError,
    RemediationPushUnavailableError,
)
from vibeguard.engine.remediation_generation import RepositoryNotReadyForRemediationError
from vibeguard.engine.vuln_scan import RepositoryNotFoundError

_TEST_ENCRYPTION_KEY = SecretStr("lvk_pkjO7PGb7TsXVDj9B59YXFJTAI8nO_gyK1nGLd4=")


def _build_test_app(
    db_session: Session,
    llm_client: httpx.Client,
    github_client: httpx.Client,
    settings: Settings,
    current_user: UserModel | None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RepositoryNotFoundError, handle_repository_not_found)
    app.add_exception_handler(
        RepositoryNotReadyForRemediationError, handle_repository_not_ready_for_remediation
    )
    app.add_exception_handler(UnauthenticatedError, handle_unauthenticated)
    app.add_exception_handler(RemediationNotFoundError, handle_remediation_not_found)
    app.add_exception_handler(RemediationAlreadyDecidedError, handle_remediation_already_decided)
    app.add_exception_handler(RemediationPushConflictError, handle_remediation_push_conflict)
    app.add_exception_handler(
        RemediationPushPermissionDeniedError, handle_remediation_push_permission_denied
    )
    app.add_exception_handler(RemediationPushUnavailableError, handle_remediation_push_unavailable)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    app.dependency_overrides[get_github_client] = lambda: github_client
    app.dependency_overrides[get_settings] = lambda: settings
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user
    return app


def _make_repository(
    session: Session, status: RepositoryStatus = RepositoryStatus.SCANNED
) -> RepositoryModel:
    repository = RepositoryModel(
        source_url="u", owner="octocat", name="Hello-World", status=status
    )
    session.add(repository)
    session.flush()
    return repository


def _make_user(session: Session, *, raw_token: str = "gho_realtoken") -> UserModel:
    ciphertext = encrypt_token(raw_token, _TEST_ENCRYPTION_KEY)
    return upsert_user_from_github_login(session, 1, "octocat", ciphertext, "public_repo")


def _make_finding(
    session: Session, repository: RepositoryModel, relative_path: str = "app.py"
) -> None:
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
    insert_findings(session, repository.id, [finding])


def _make_remediation(session: Session, repository: RepositoryModel) -> int:
    proposal = RemediationProposal(
        relative_path="app.py",
        original_content="original",
        proposed_content="proposed",
        diff_text="diff",
        summary="s",
        model="m",
        finding_ids=(),
        introduces_new_heuristic_hits=False,
        new_heuristic_hit_summary=None,
    )
    remediation = insert_remediation(session, repository.id, proposal)
    session.commit()
    return remediation.id


def test_remediate_repository_requires_authentication(db_session: Session, settings_factory):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.post("/repositories/1/remediate")
    assert response.status_code == 401


def test_list_remediations_requires_authentication(db_session: Session, settings_factory):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.get("/repositories/1/remediations")
    assert response.status_code == 401


def test_approve_requires_authentication(db_session: Session, settings_factory):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.post("/remediations/1/approve", json={})
    assert response.status_code == 401


def test_reject_requires_authentication(db_session: Session, settings_factory):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.post("/remediations/1/reject", json={})
    assert response.status_code == 401


def test_remediate_repository_malformed_authorization_header_returns_401(
    db_session: Session, settings_factory
):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.post(
        "/repositories/1/remediate", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert response.status_code == 401


def test_remediate_repository_bearer_header_with_no_token_returns_401(
    db_session: Session, settings_factory
):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), None)
    )
    response = client.post("/repositories/1/remediate", headers={"Authorization": "Bearer "})
    assert response.status_code == 401


def test_remediate_repository_unknown_id_returns_404(db_session: Session, settings_factory):
    user = _make_user(db_session)
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post("/repositories/999999/remediate")
    assert response.status_code == 404


def test_remediate_repository_not_scanned_returns_409(db_session: Session, settings_factory):
    user = _make_user(db_session)
    repository = _make_repository(db_session, RepositoryStatus.SCANNING)
    db_session.commit()
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post(f"/repositories/{repository.id}/remediate")
    assert response.status_code == 409


def test_remediate_repository_happy_path_persists_and_returns_remediations(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id, relative_path="app.py", size_bytes=10, content="original"
        )
    )
    db_session.flush()
    _make_finding(db_session, repository)
    db_session.commit()

    monkeypatch.setattr(
        remediation_generation_module,
        "generate_remediation",
        Mock(return_value=GeneratedRemediation(proposed_content="fixed", summary="s")),
    )

    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post(f"/repositories/{repository.id}/remediate")

    assert response.status_code == 200
    body = response.json()
    assert body["attempted"] == 1
    assert body["succeeded"] == 1
    assert len(body["remediations"]) == 1
    assert body["remediations"][0]["proposed_content"] == "fixed"


def test_list_remediations_returns_newest_first(db_session: Session, settings_factory):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.commit()
    first_id = _make_remediation(db_session, repository)
    second_id = _make_remediation(db_session, repository)

    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.get(f"/repositories/{repository.id}/remediations")

    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["remediations"]]
    assert ids == [second_id, first_id]


def test_approve_missing_remediation_returns_404(db_session: Session, settings_factory):
    user = _make_user(db_session)
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post("/remediations/999999/approve", json={})
    assert response.status_code == 404


def test_approve_already_decided_returns_409(db_session: Session, settings_factory):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.commit()
    remediation_id = _make_remediation(db_session, repository)
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    client.post(f"/remediations/{remediation_id}/reject", json={})

    response = client.post(f"/remediations/{remediation_id}/approve", json={})

    assert response.status_code == 409


def test_approve_happy_path_returns_pushed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.commit()
    remediation_id = _make_remediation(db_session, repository)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(return_value=PushedCommit(commit_sha="commit1")),
    )

    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post(f"/remediations/{remediation_id}/approve", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pushed"
    assert body["pushed_commit_sha"] == "commit1"


def test_approve_conflict_returns_409_and_persists_push_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.commit()
    remediation_id = _make_remediation(db_session, repository)

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", Mock(return_value="main")
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(side_effect=GitHubPushConflictError("stale")),
    )

    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post(f"/remediations/{remediation_id}/approve", json={})

    assert response.status_code == 409

    persisted = get_remediation_by_id(db_session, remediation_id)
    assert persisted is not None
    assert persisted.status == RemediationStatus.PUSH_FAILED


def test_reject_happy_path_returns_rejected(db_session: Session, settings_factory):
    user = _make_user(db_session)
    repository = _make_repository(db_session)
    db_session.commit()
    remediation_id = _make_remediation(db_session, repository)

    client = TestClient(
        _build_test_app(db_session, httpx.Client(), httpx.Client(), settings_factory(), user)
    )
    response = client.post(
        f"/remediations/{remediation_id}/reject", json={"decision_reason": "not needed"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["decision_reason"] == "not needed"


def test_approve_uses_approving_users_own_token(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    # Two distinct users exist; the one authenticated on this request is
    # the one whose token must be used to push -- a deliberate design
    # decision worth its own regression test.
    _make_user(db_session, raw_token="gho_someone_elses_token")
    approving_user = _make_user_with_github_id(
        db_session, github_user_id=2, raw_token="gho_approver_token"
    )
    repository = _make_repository(db_session)
    db_session.commit()
    remediation_id = _make_remediation(db_session, repository)

    seen_tokens = []

    def fake_fetch_default_branch(owner, repo, access_token, client, timeout_seconds):
        seen_tokens.append(access_token)
        return "main"

    monkeypatch.setattr(
        remediation_decision_module, "fetch_default_branch", fake_fetch_default_branch
    )
    monkeypatch.setattr(remediation_decision_module, "fetch_file_sha", Mock(return_value="sha1"))
    monkeypatch.setattr(
        remediation_decision_module,
        "push_file_update",
        Mock(return_value=PushedCommit(commit_sha="commit1")),
    )

    client = TestClient(
        _build_test_app(
            db_session, httpx.Client(), httpx.Client(), settings_factory(), approving_user
        )
    )
    response = client.post(f"/remediations/{remediation_id}/approve", json={})

    assert response.status_code == 200
    assert seen_tokens == ["gho_approver_token"]


def _make_user_with_github_id(
    session: Session, *, github_user_id: int, raw_token: str
) -> UserModel:
    ciphertext = encrypt_token(raw_token, _TEST_ENCRYPTION_KEY)
    return upsert_user_from_github_login(
        session, github_user_id, f"user{github_user_id}", ciphertext, "public_repo"
    )
