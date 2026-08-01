"""Tests for POST /repositories through the full request/response cycle."""

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import vibeguard.engine.intake as intake_module
from tests.conftest import make_mock_http_client
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.adapters.github.clone import CloneFailedError
from vibeguard.api.dependencies import get_db_session, get_github_client, get_settings
from vibeguard.api.error_handlers import (
    handle_github_api_unavailable,
    handle_invalid_repository_url,
)
from vibeguard.api.routes.repositories import router
from vibeguard.core.github_url import InvalidRepositoryUrlError


def _build_test_app(
    db_session: Session, github_client: httpx.Client, settings: Settings
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(InvalidRepositoryUrlError, handle_invalid_repository_url)
    app.add_exception_handler(GitHubApiUnavailableError, handle_github_api_unavailable)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_github_client] = lambda: github_client
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def _mock_github(
    *, private: bool = False, size_kb: int = 10, status_code: int = 200
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if status_code != 200:
            return httpx.Response(status_code)
        return httpx.Response(200, json={"private": private, "size": size_kb})

    return make_mock_http_client(handler)


def test_submit_repository_happy_path_returns_201(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch, local_bare_repo: Path
):
    settings = settings_factory()
    github_client = _mock_github()
    real_clone = intake_module.clone_repository

    def _clone_local(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        real_clone(str(local_bare_repo), destination, timeout_seconds)

    monkeypatch.setattr(intake_module, "clone_repository", _clone_local)

    client = TestClient(_build_test_app(db_session, github_client, settings))
    response = client.post("/repositories", json={"repo_url": "https://github.com/octocat/Hello-World"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scan_pending_implementation"
    assert body["total_files_stored"] == 2


def test_submit_repository_malformed_url_returns_422(db_session: Session, settings_factory):
    settings = settings_factory()
    client = TestClient(_build_test_app(db_session, _mock_github(), settings))

    response = client.post("/repositories", json={"repo_url": "https://evil.example.com/o/r"})

    assert response.status_code == 422


def test_submit_repository_github_unavailable_returns_502(db_session: Session, settings_factory):
    settings = settings_factory()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = TestClient(_build_test_app(db_session, make_mock_http_client(handler), settings))
    response = client.post("/repositories", json={"repo_url": "https://github.com/octocat/Hello-World"})

    assert response.status_code == 502


def test_submit_repository_private_repo_returns_201_rejected(db_session: Session, settings_factory):
    settings = settings_factory()
    client = TestClient(_build_test_app(db_session, _mock_github(private=True), settings))

    response = client.post("/repositories", json={"repo_url": "https://github.com/octocat/secret"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "not_public_or_not_found"


def test_submit_repository_clone_failure_returns_201_rejected(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_factory()

    def _raise(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        raise CloneFailedError("simulated")

    monkeypatch.setattr(intake_module, "clone_repository", _raise)

    client = TestClient(_build_test_app(db_session, _mock_github(), settings))
    response = client.post("/repositories", json={"repo_url": "https://github.com/octocat/Hello-World"})

    assert response.status_code == 201
    assert response.json()["rejection_reason"] == "clone_failed"


def test_submit_repository_missing_body_field_returns_422(db_session: Session, settings_factory):
    settings = settings_factory()
    client = TestClient(_build_test_app(db_session, _mock_github(), settings))

    response = client.post("/repositories", json={})

    assert response.status_code == 422
