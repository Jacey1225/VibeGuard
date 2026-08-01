"""Tests for the GitHub OAuth adapter, entirely network-free."""

import httpx
import pytest
from pydantic import SecretStr

from tests.conftest import make_mock_http_client
from vibeguard.adapters.auth.github_oauth_client import (
    GitHubOAuthResponseParseError,
    GitHubOAuthUnavailableError,
    build_authorize_url,
    exchange_code_for_token,
    fetch_github_user,
)

_CLIENT_SECRET = SecretStr("test-client-secret")


def test_build_authorize_url_includes_required_params():
    url = build_authorize_url(
        "client-123", "http://localhost:8000/auth/github/callback", "state-abc"
    )
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert "client_id=client-123" in url
    assert "scope=public_repo" in url
    assert "state=state-abc" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000" in url


def test_exchange_code_for_token_happy_path():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "gho_abc123", "scope": "public_repo"})

    client = make_mock_http_client(handler)
    token = exchange_code_for_token(
        "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
    )
    assert token.access_token == "gho_abc123"  # noqa: S105 (test fixture, not a real credential)
    assert token.scope == "public_repo"


def test_exchange_code_for_token_github_error_shape_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "bad_verification_code"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthResponseParseError, match="bad_verification_code"):
        exchange_code_for_token(
            "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
        )


def test_exchange_code_for_token_missing_field_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"scope": "public_repo"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthResponseParseError):
        exchange_code_for_token(
            "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
        )


def test_exchange_code_for_token_malformed_json_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthResponseParseError):
        exchange_code_for_token(
            "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
        )


def test_exchange_code_for_token_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthUnavailableError):
        exchange_code_for_token(
            "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
        )


def test_exchange_code_for_token_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthUnavailableError):
        exchange_code_for_token(
            "code", "client-id", _CLIENT_SECRET, "http://localhost/callback", client, 5.0
        )


def test_fetch_github_user_happy_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer gho_abc123"
        return httpx.Response(200, json={"id": 42, "login": "octocat"})

    client = make_mock_http_client(handler)
    profile = fetch_github_user("gho_abc123", client, 5.0)
    assert profile.id == 42
    assert profile.login == "octocat"


def test_fetch_github_user_unauthorized_raises_parse_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthResponseParseError):
        fetch_github_user("bad-token", client, 5.0)


def test_fetch_github_user_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubOAuthUnavailableError):
        fetch_github_user("token", client, 5.0)
