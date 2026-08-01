"""Tests for GitHub OAuth login/callback and logout."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import vibeguard.api.routes.auth as auth_route_module
from vibeguard.adapters.auth.github_oauth_client import GitHubOAuthToken, GitHubUserProfile
from vibeguard.adapters.auth.session_token import generate_session_token, hash_session_token
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.session_store import get_valid_session_by_token_hash, insert_session
from vibeguard.adapters.db.user_store import upsert_user_from_github_login
from vibeguard.api.auth_dependencies import UnauthenticatedError
from vibeguard.api.dependencies import get_db_session, get_github_client, get_settings
from vibeguard.api.error_handlers import handle_unauthenticated
from vibeguard.api.routes.auth import router


def _build_test_app(
    db_session: Session, github_client: httpx.Client, settings: Settings
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(UnauthenticatedError, handle_unauthenticated)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_github_client] = lambda: github_client
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def test_start_github_login_redirects_with_state_cookie(db_session: Session, settings_factory):
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), settings_factory()), follow_redirects=False
    )

    response = client.get("/auth/github/login")

    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize?")
    assert "vibeguard_oauth_state" in response.cookies


def test_callback_missing_state_cookie_returns_401(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.get("/auth/github/callback", params={"code": "c", "state": "s"})

    assert response.status_code == 401


def test_callback_mismatched_state_returns_401_without_calling_github(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    exchange_spy = Mock()
    monkeypatch.setattr(auth_route_module, "exchange_code_for_token", exchange_spy)
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    client.cookies.set("vibeguard_oauth_state", "cookie-value")

    response = client.get(
        "/auth/github/callback", params={"code": "c", "state": "different-value"}
    )

    assert response.status_code == 401
    exchange_spy.assert_not_called()


def test_callback_happy_path_creates_user_and_redirects_with_session_token(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        auth_route_module,
        "exchange_code_for_token",
        Mock(return_value=GitHubOAuthToken(access_token="gho_realtoken", scope="public_repo")),
    )
    monkeypatch.setattr(
        auth_route_module,
        "fetch_github_user",
        Mock(return_value=GitHubUserProfile(id=42, login="octocat")),
    )
    settings = settings_factory()
    client = TestClient(
        _build_test_app(db_session, httpx.Client(), settings), follow_redirects=False
    )
    client.cookies.set("vibeguard_oauth_state", "matching-state")

    response = client.get(
        "/auth/github/callback", params={"code": "c", "state": "matching-state"}
    )

    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert location.startswith(f"{settings.frontend_redirect_base_url}#session_token=")

    raw_token = location.split("#session_token=", 1)[1]
    session_row = get_valid_session_by_token_hash(
        db_session, hash_session_token(raw_token), datetime.now(UTC)
    )
    assert session_row is not None


def test_logout_deletes_session_and_subsequent_call_is_unauthenticated(
    db_session: Session, settings_factory
):
    user = upsert_user_from_github_login(
        db_session, 1, "octocat", "ciphertext", "public_repo"
    )
    raw_token = generate_session_token()
    insert_session(
        db_session, user.id, hash_session_token(raw_token), datetime.now(UTC) + timedelta(hours=1)
    )
    db_session.commit()

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {raw_token}"})
    assert response.status_code == 204

    second_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {raw_token}"})
    assert second_response.status_code == 401


def test_logout_missing_authorization_header_returns_401(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post("/auth/logout")

    assert response.status_code == 401
