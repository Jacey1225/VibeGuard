"""Tests for the GitHub API public/existence check adapter."""

import httpx
import pytest

from tests.conftest import make_mock_github_client
from vibeguard.adapters.github.client import GitHubApiUnavailableError, fetch_repository_metadata


def test_fetch_repository_metadata_public_repo():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"private": False, "size": 42})

    client = make_mock_github_client(handler)
    metadata = fetch_repository_metadata("octocat", "Hello-World", client, timeout_seconds=5.0)
    assert metadata.exists_and_public is True
    assert metadata.size_kb == 42


def test_fetch_repository_metadata_private_repo():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"private": True, "size": 10})

    client = make_mock_github_client(handler)
    metadata = fetch_repository_metadata("octocat", "secret-repo", client, timeout_seconds=5.0)
    assert metadata.exists_and_public is False


def test_fetch_repository_metadata_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = make_mock_github_client(handler)
    metadata = fetch_repository_metadata("octocat", "nope", client, timeout_seconds=5.0)
    assert metadata.exists_and_public is False
    assert metadata.size_kb == 0


def test_fetch_repository_metadata_server_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    client = make_mock_github_client(handler)
    with pytest.raises(GitHubApiUnavailableError):
        fetch_repository_metadata("octocat", "Hello-World", client, timeout_seconds=5.0)


def test_fetch_repository_metadata_network_error_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_github_client(handler)
    with pytest.raises(GitHubApiUnavailableError):
        fetch_repository_metadata("octocat", "Hello-World", client, timeout_seconds=5.0)


def test_fetch_repository_metadata_malformed_body_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    client = make_mock_github_client(handler)
    with pytest.raises(GitHubApiUnavailableError):
        fetch_repository_metadata("octocat", "Hello-World", client, timeout_seconds=5.0)


def test_fetch_repository_metadata_sends_required_user_agent_header():
    seen_headers = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(200, json={"private": False, "size": 0})

    client = make_mock_github_client(handler)
    fetch_repository_metadata("octocat", "Hello-World", client, timeout_seconds=5.0)
    assert "user-agent" in seen_headers
