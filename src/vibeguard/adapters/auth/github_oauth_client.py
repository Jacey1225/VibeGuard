"""GitHub OAuth: authorize-URL building, code-for-token exchange, profile fetch.

Requests `public_repo` scope only — write access to public
repositories, matching VibeGuard's existing "repo must be public"
constraint elsewhere. Never full `repo` scope; no reason to.
"""

from __future__ import annotations

from urllib.parse import quote

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105 (URL, not a credential)
_USER_URL = "https://api.github.com/user"
_OAUTH_SCOPE = "public_repo"


class GitHubOAuthUnavailableError(RuntimeError):
    """Raised when a GitHub OAuth endpoint can't be reached or fails unexpectedly."""


class GitHubOAuthResponseParseError(RuntimeError):
    """Raised when a GitHub OAuth response isn't valid, schema-conforming JSON."""


class GitHubOAuthToken(BaseModel):
    """The token-exchange response."""

    access_token: str
    scope: str


class GitHubUserProfile(BaseModel):
    """The authenticated user's GitHub profile."""

    id: int
    login: str


def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Build the URL to redirect the browser to for GitHub's consent screen."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": _OAUTH_SCOPE,
        "state": state,
    }
    query = "&".join(f"{key}={quote(value, safe='')}" for key, value in params.items())
    return f"{_AUTHORIZE_URL}?{query}"


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: SecretStr,
    redirect_uri: str,
    client: httpx.Client,
    timeout_seconds: float,
) -> GitHubOAuthToken:
    """Exchange an OAuth authorization code for an access token.

    Raises:
        GitHubOAuthUnavailableError: network failure, timeout, or a
            provider-side (5xx) error.
        GitHubOAuthResponseParseError: the response wasn't valid,
            schema-conforming JSON — including GitHub's own
            `{"error": ...}` shape for a rejected/expired code.
    """
    response = _request_token(code, client_id, client_secret, redirect_uri, client, timeout_seconds)
    return _parse_token_response(response)


def _request_token(
    code: str,
    client_id: str,
    client_secret: SecretStr,
    redirect_uri: str,
    client: httpx.Client,
    timeout_seconds: float,
) -> httpx.Response:
    try:
        return client.post(
            _TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": redirect_uri,
            },
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubOAuthUnavailableError(f"GitHub OAuth token request failed: {error}") from error


def _parse_token_response(response: httpx.Response) -> GitHubOAuthToken:
    if response.status_code >= 500:
        raise GitHubOAuthUnavailableError(
            f"GitHub OAuth token endpoint returned {response.status_code}"
        )

    try:
        body = response.json()
    except ValueError as error:
        raise GitHubOAuthResponseParseError(
            f"GitHub OAuth token response wasn't valid JSON: {error}"
        ) from error

    if isinstance(body, dict) and "error" in body:
        raise GitHubOAuthResponseParseError(f"GitHub OAuth rejected the request: {body['error']}")

    try:
        return GitHubOAuthToken.model_validate(body)
    except ValidationError as error:
        raise GitHubOAuthResponseParseError(
            f"GitHub OAuth token response missing expected fields: {error}"
        ) from error


def fetch_github_user(
    access_token: str, client: httpx.Client, timeout_seconds: float
) -> GitHubUserProfile:
    """Fetch the authenticated user's GitHub profile.

    Raises:
        GitHubOAuthUnavailableError: network failure, timeout, or a
            provider-side (5xx) error.
        GitHubOAuthResponseParseError: the response wasn't valid,
            schema-conforming JSON.
    """
    response = _request_user(access_token, client, timeout_seconds)
    return _parse_user_response(response)


def _request_user(
    access_token: str, client: httpx.Client, timeout_seconds: float
) -> httpx.Response:
    try:
        return client.get(
            _USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubOAuthUnavailableError(f"GitHub user profile request failed: {error}") from error


def _parse_user_response(response: httpx.Response) -> GitHubUserProfile:
    if response.status_code >= 500:
        raise GitHubOAuthUnavailableError(f"GitHub user profile returned {response.status_code}")
    if response.status_code != 200:
        raise GitHubOAuthResponseParseError(f"GitHub user profile returned {response.status_code}")

    try:
        return GitHubUserProfile.model_validate_json(response.content)
    except ValidationError as error:
        raise GitHubOAuthResponseParseError(
            f"GitHub user profile response missing expected fields: {error}"
        ) from error
