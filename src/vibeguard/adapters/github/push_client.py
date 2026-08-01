"""Pushing an approved remediation to GitHub via the Contents API.

The Contents API (`PUT /repos/{owner}/{repo}/contents/{path}`) is used
over a local clone-and-push: at this feature's one-fix-per-file
granularity it's a single read-sha/write-content HTTP call, with no
local clone, no subprocess, and critically no decrypted token ever
touching disk or a `git`-credential-in-URL.

Kept separate from `client.py`/`clone.py` rather than extending them —
those are unauthenticated, read-only intake adapters; this one carries
a live per-user write credential and a materially different failure
model (conflicts, permission checks) that intake never has to handle.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

_USER_AGENT = "VibeGuard-Remediation"


class GitHubPushUnavailableError(RuntimeError):
    """Raised on network failure, timeout, or a GitHub-side (5xx) error."""


class GitHubPushConflictError(RuntimeError):
    """Raised when the target file has changed since this proposal was based on it."""


class GitHubPushPermissionDeniedError(RuntimeError):
    """Raised when the approving user's token can't write to this repository."""


@dataclass(frozen=True)
class PushedCommit:
    """The outcome of a successful push."""

    commit_sha: str


def fetch_default_branch(
    owner: str, repo: str, access_token: str, client: httpx.Client, timeout_seconds: float
) -> str:
    """Fetch a repository's current default branch, fresh, never cached.

    Raises:
        GitHubPushUnavailableError: network failure, timeout, or a
            provider-side (5xx) error.
        GitHubPushPermissionDeniedError: the repository doesn't exist
            or this token can't see it (GitHub returns 404 for both).
    """
    try:
        response = client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=_auth_headers(access_token),
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubPushUnavailableError(f"GitHub repository lookup failed: {error}") from error

    if response.status_code >= 500:
        raise GitHubPushUnavailableError(
            f"GitHub repository lookup returned {response.status_code}"
        )
    if response.status_code in (403, 404):
        raise GitHubPushPermissionDeniedError(
            f"GitHub repository lookup returned {response.status_code}"
        )
    if response.status_code != 200:
        raise GitHubPushUnavailableError(
            f"GitHub repository lookup returned {response.status_code}"
        )

    try:
        branch: str = response.json()["default_branch"]
    except (ValueError, KeyError, TypeError) as error:
        raise GitHubPushUnavailableError(
            f"GitHub repository lookup returned an unexpected body: {error}"
        ) from error
    return branch


def fetch_file_sha(
    owner: str,
    repo: str,
    relative_path: str,
    branch: str,
    access_token: str,
    client: httpx.Client,
    timeout_seconds: float,
) -> str:
    """Fetch a file's current blob sha on a branch, fetched fresh immediately before a write.

    Raises:
        GitHubPushUnavailableError: network failure, timeout, or a
            provider-side (5xx) error.
        GitHubPushConflictError: the file no longer exists at this path
            on this branch — the proposal this push is based on is
            stale.
        GitHubPushPermissionDeniedError: this token can't read the
            file's containing repository.
    """
    try:
        response = client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{relative_path}",
            headers=_auth_headers(access_token),
            params={"ref": branch},
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubPushUnavailableError(f"GitHub file lookup failed: {error}") from error

    if response.status_code >= 500:
        raise GitHubPushUnavailableError(f"GitHub file lookup returned {response.status_code}")
    if response.status_code == 404:
        raise GitHubPushConflictError(f"{relative_path} no longer exists on branch {branch}")
    if response.status_code == 403:
        raise GitHubPushPermissionDeniedError("GitHub file lookup returned 403")
    if response.status_code != 200:
        raise GitHubPushUnavailableError(f"GitHub file lookup returned {response.status_code}")

    try:
        sha: str = response.json()["sha"]
    except (ValueError, KeyError, TypeError) as error:
        raise GitHubPushUnavailableError(
            f"GitHub file lookup returned an unexpected body: {error}"
        ) from error
    return sha


def push_file_update(
    owner: str,
    repo: str,
    relative_path: str,
    branch: str,
    content: str,
    sha: str,
    commit_message: str,
    access_token: str,
    client: httpx.Client,
    timeout_seconds: float,
) -> PushedCommit:
    """Write a file's new content as a commit on a branch via the Contents API.

    `sha` must be the file's current blob sha, fetched immediately
    before this call (`fetch_file_sha`) — GitHub rejects the write with
    409 if it no longer matches, which is the real, final conflict
    check; no automatic merge is ever attempted on that signal.

    Raises:
        GitHubPushUnavailableError: network failure, timeout, or a
            provider-side (5xx) error.
        GitHubPushConflictError: `sha` no longer matches the file's
            current content on GitHub.
        GitHubPushPermissionDeniedError: this token doesn't have write
            access to this repository.
    """
    try:
        response = client.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{relative_path}",
            headers=_auth_headers(access_token),
            json={
                "message": commit_message,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "sha": sha,
                "branch": branch,
            },
            timeout=timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise GitHubPushUnavailableError(f"GitHub file push failed: {error}") from error

    if response.status_code >= 500:
        raise GitHubPushUnavailableError(f"GitHub file push returned {response.status_code}")
    if response.status_code == 409:
        raise GitHubPushConflictError(f"{relative_path} was modified since {sha} was fetched")
    if response.status_code in (403, 404):
        raise GitHubPushPermissionDeniedError(f"GitHub file push returned {response.status_code}")
    if response.status_code not in (200, 201):
        raise GitHubPushUnavailableError(f"GitHub file push returned {response.status_code}")

    try:
        commit_sha: str = response.json()["commit"]["sha"]
    except (ValueError, KeyError, TypeError) as error:
        raise GitHubPushUnavailableError(
            f"GitHub file push returned an unexpected body: {error}"
        ) from error
    return PushedCommit(commit_sha=commit_sha)


def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        "User-Agent": _USER_AGENT,
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }
