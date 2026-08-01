"""Tests for exception -> HTTP status mapping."""

import asyncio
import json

from vibeguard.adapters.auth.github_oauth_client import (
    GitHubOAuthResponseParseError,
    GitHubOAuthUnavailableError,
)
from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.api.auth_dependencies import UnauthenticatedError
from vibeguard.api.error_handlers import (
    handle_github_api_unavailable,
    handle_github_oauth_login_failed,
    handle_github_oauth_unavailable,
    handle_invalid_repository_url,
    handle_remediation_already_decided,
    handle_remediation_not_found,
    handle_remediation_push_conflict,
    handle_remediation_push_permission_denied,
    handle_remediation_push_unavailable,
    handle_repository_not_ready_for_remediation,
    handle_unauthenticated,
)
from vibeguard.core.github_url import InvalidRepositoryUrlError
from vibeguard.engine.remediation_decision import (
    RemediationAlreadyDecidedError,
    RemediationNotFoundError,
    RemediationPushConflictError,
    RemediationPushPermissionDeniedError,
    RemediationPushUnavailableError,
)
from vibeguard.engine.remediation_generation import RepositoryNotReadyForRemediationError


def test_handle_invalid_repository_url_returns_422():
    exc = InvalidRepositoryUrlError("bad url")
    response = asyncio.run(handle_invalid_repository_url(None, exc))
    assert response.status_code == 422
    assert json.loads(response.body)["detail"] == "bad url"


def test_handle_github_api_unavailable_returns_502_generic_message():
    response = asyncio.run(handle_github_api_unavailable(None, GitHubApiUnavailableError("boom")))
    assert response.status_code == 502
    assert "unavailable" in json.loads(response.body)["detail"].lower()


def test_handle_repository_not_ready_for_remediation_returns_409():
    response = asyncio.run(
        handle_repository_not_ready_for_remediation(
            None, RepositoryNotReadyForRemediationError("not scanned")
        )
    )
    assert response.status_code == 409
    assert json.loads(response.body)["detail"] == "not scanned"


def test_handle_unauthenticated_returns_401():
    response = asyncio.run(handle_unauthenticated(None, UnauthenticatedError("no token")))
    assert response.status_code == 401
    assert json.loads(response.body)["detail"] == "no token"


def test_handle_github_oauth_unavailable_returns_502():
    response = asyncio.run(
        handle_github_oauth_unavailable(None, GitHubOAuthUnavailableError("down"))
    )
    assert response.status_code == 502


def test_handle_github_oauth_login_failed_returns_401():
    response = asyncio.run(
        handle_github_oauth_login_failed(None, GitHubOAuthResponseParseError("bad code"))
    )
    assert response.status_code == 401


def test_handle_remediation_not_found_returns_404():
    response = asyncio.run(
        handle_remediation_not_found(None, RemediationNotFoundError("no remediation 1"))
    )
    assert response.status_code == 404
    assert json.loads(response.body)["detail"] == "no remediation 1"


def test_handle_remediation_already_decided_returns_409():
    response = asyncio.run(
        handle_remediation_already_decided(None, RemediationAlreadyDecidedError("already pushed"))
    )
    assert response.status_code == 409


def test_handle_remediation_push_conflict_returns_409_with_regenerate_hint():
    response = asyncio.run(
        handle_remediation_push_conflict(None, RemediationPushConflictError("stale"))
    )
    assert response.status_code == 409
    assert "regenerate" in json.loads(response.body)["detail"].lower()


def test_handle_remediation_push_permission_denied_returns_403():
    response = asyncio.run(
        handle_remediation_push_permission_denied(
            None, RemediationPushPermissionDeniedError("forbidden")
        )
    )
    assert response.status_code == 403


def test_handle_remediation_push_unavailable_returns_502():
    response = asyncio.run(
        handle_remediation_push_unavailable(None, RemediationPushUnavailableError("down"))
    )
    assert response.status_code == 502
