"""Live check against the GitHub API for a repository's existence and visibility."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

_USER_AGENT = "VibeGuard-Intake"


class GitHubApiUnavailableError(RuntimeError):
    """Raised when the GitHub API can't be reached or fails unexpectedly."""


@dataclass(frozen=True)
class GitHubRepoMetadata:
    """What GitHub reports about a repository, relevant to intake."""

    exists_and_public: bool
    size_kb: int


def fetch_repository_metadata(
    owner: str,
    repo: str,
    client: httpx.Client,
    timeout_seconds: float,
) -> GitHubRepoMetadata:
    """Fetch a repository's public existence and reported size from GitHub.

    Raises:
        GitHubApiUnavailableError: on network failure, timeout, a
            GitHub-side (5xx) error, or an unparseable response body —
            an infrastructure problem distinct from "repository not
            found/private," which is a valid outcome carried in the
            returned metadata instead.
    """
    response = _request_repository(owner, repo, client, timeout_seconds)
    return _parse_repository_metadata(response)


def _request_repository(
    owner: str, repo: str, client: httpx.Client, timeout_seconds: float
) -> httpx.Response:
    try:
        return client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"},
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubApiUnavailableError(f"GitHub API request failed: {error}") from error


def _parse_repository_metadata(response: httpx.Response) -> GitHubRepoMetadata:
    if response.status_code == 404:
        return GitHubRepoMetadata(exists_and_public=False, size_kb=0)
    if response.status_code >= 500:
        raise GitHubApiUnavailableError(f"GitHub API returned {response.status_code}")
    if response.status_code != 200:
        return GitHubRepoMetadata(exists_and_public=False, size_kb=0)

    try:
        body = response.json()
        is_private = bool(body.get("private", True))
        size_kb = int(body.get("size", 0))
    except (ValueError, TypeError, AttributeError) as error:
        raise GitHubApiUnavailableError(
            f"GitHub API returned an unparseable body: {error}"
        ) from error

    return GitHubRepoMetadata(exists_and_public=not is_private, size_kb=size_kb)
