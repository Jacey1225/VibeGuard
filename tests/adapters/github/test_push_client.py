"""Tests for the GitHub push adapter, entirely network-free."""

import base64
import json

import httpx
import pytest

from tests.conftest import make_mock_http_client
from vibeguard.adapters.github.push_client import (
    GitHubPushConflictError,
    GitHubPushPermissionDeniedError,
    GitHubPushUnavailableError,
    fetch_default_branch,
    fetch_file_sha,
    push_file_update,
)


def test_fetch_default_branch_happy_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer gho_abc123"
        return httpx.Response(200, json={"default_branch": "main"})

    client = make_mock_http_client(handler)
    branch = fetch_default_branch("octocat", "Hello-World", "gho_abc123", client, 5.0)
    assert branch == "main"


def test_fetch_default_branch_404_raises_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushPermissionDeniedError):
        fetch_default_branch("octocat", "Hello-World", "gho_abc123", client, 5.0)


def test_fetch_default_branch_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushUnavailableError):
        fetch_default_branch("octocat", "Hello-World", "gho_abc123", client, 5.0)


def test_fetch_default_branch_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushUnavailableError):
        fetch_default_branch("octocat", "Hello-World", "gho_abc123", client, 5.0)


def test_fetch_file_sha_happy_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["ref"] == "main"
        return httpx.Response(200, json={"sha": "abc123"})

    client = make_mock_http_client(handler)
    sha = fetch_file_sha("octocat", "Hello-World", "app.py", "main", "gho_abc123", client, 5.0)
    assert sha == "abc123"


def test_fetch_file_sha_missing_file_raises_conflict():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushConflictError):
        fetch_file_sha("octocat", "Hello-World", "app.py", "main", "gho_abc123", client, 5.0)


def test_fetch_file_sha_forbidden_raises_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushPermissionDeniedError):
        fetch_file_sha("octocat", "Hello-World", "app.py", "main", "gho_abc123", client, 5.0)


def test_fetch_file_sha_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushUnavailableError):
        fetch_file_sha("octocat", "Hello-World", "app.py", "main", "gho_abc123", client, 5.0)


def test_push_file_update_happy_path_base64_encodes_content():
    seen_bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"commit": {"sha": "def456"}})

    client = make_mock_http_client(handler)
    result = push_file_update(
        "octocat",
        "Hello-World",
        "app.py",
        "main",
        "print('fixed')",
        "abc123",
        "Fix SQL injection",
        "gho_abc123",
        client,
        5.0,
    )

    assert result.commit_sha == "def456"
    body = seen_bodies[0]
    assert body["sha"] == "abc123"
    assert body["branch"] == "main"
    assert body["message"] == "Fix SQL injection"
    assert base64.b64decode(body["content"]).decode("utf-8") == "print('fixed')"


def test_push_file_update_conflict_raises_conflict_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"message": "sha does not match"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushConflictError):
        push_file_update(
            "octocat",
            "Hello-World",
            "app.py",
            "main",
            "content",
            "stale-sha",
            "msg",
            "gho_abc123",
            client,
            5.0,
        )


def test_push_file_update_forbidden_raises_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushPermissionDeniedError):
        push_file_update(
            "octocat",
            "Hello-World",
            "app.py",
            "main",
            "content",
            "sha",
            "msg",
            "gho_abc123",
            client,
            5.0,
        )


def test_push_file_update_not_found_raises_permission_denied():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushPermissionDeniedError):
        push_file_update(
            "octocat",
            "Hello-World",
            "app.py",
            "main",
            "content",
            "sha",
            "msg",
            "gho_abc123",
            client,
            5.0,
        )


def test_push_file_update_server_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="unavailable")

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushUnavailableError):
        push_file_update(
            "octocat",
            "Hello-World",
            "app.py",
            "main",
            "content",
            "sha",
            "msg",
            "gho_abc123",
            client,
            5.0,
        )


def test_push_file_update_network_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_http_client(handler)
    with pytest.raises(GitHubPushUnavailableError):
        push_file_update(
            "octocat",
            "Hello-World",
            "app.py",
            "main",
            "content",
            "sha",
            "msg",
            "gho_abc123",
            client,
            5.0,
        )
