"""Tests for exception -> HTTP status mapping."""

import asyncio
import json

from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.api.error_handlers import (
    handle_github_api_unavailable,
    handle_invalid_repository_url,
)
from vibeguard.core.github_url import InvalidRepositoryUrlError


def test_handle_invalid_repository_url_returns_422():
    exc = InvalidRepositoryUrlError("bad url")
    response = asyncio.run(handle_invalid_repository_url(None, exc))
    assert response.status_code == 422
    assert json.loads(response.body)["detail"] == "bad url"


def test_handle_github_api_unavailable_returns_502_generic_message():
    response = asyncio.run(handle_github_api_unavailable(None, GitHubApiUnavailableError("boom")))
    assert response.status_code == 502
    assert "unavailable" in json.loads(response.body)["detail"].lower()
