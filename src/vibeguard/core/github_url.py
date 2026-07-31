"""Parsing and validating a raw string into a GitHub repository reference.

The submitted URL is fully attacker-controlled input (see code-security's
untrusted-input rules) — every check here exists to prevent that string
from resulting in a clone/request against something other than a public
github.com repository (SSRF-adjacent host confusion, embedded
credentials, path traversal via extra segments).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_OWNER_REPO_PATTERN = re.compile(
    r"^/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)"
    r"/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


class InvalidRepositoryUrlError(ValueError):
    """Raised when a submitted string isn't a valid public GitHub repo URL."""


@dataclass(frozen=True)
class GitHubRepoRef:
    """A validated reference to a GitHub repository."""

    owner: str
    repo: str

    @property
    def clone_url(self) -> str:
        """The canonical HTTPS clone URL for this repository."""
        return f"https://github.com/{self.owner}/{self.repo}.git"


def parse_github_repo_url(raw_url: str) -> GitHubRepoRef:
    """Parse and validate a raw string as a public GitHub repository URL.

    Raises:
        InvalidRepositoryUrlError: if the URL isn't a well-formed
            `https://github.com/<owner>/<repo>` reference.
    """
    parts = urlsplit(raw_url.strip())
    _require_https_scheme(parts.scheme)
    _require_github_host(parts.hostname)
    _require_no_credentials(parts.username, parts.password)
    _require_no_query_or_fragment(parts.query, parts.fragment)
    owner, repo = _parse_owner_and_repo(parts.path)
    return GitHubRepoRef(owner=owner, repo=repo)


def _require_https_scheme(scheme: str) -> None:
    if scheme.lower() != "https":
        raise InvalidRepositoryUrlError("URL must use https")


def _require_github_host(hostname: str | None) -> None:
    if hostname != "github.com":
        raise InvalidRepositoryUrlError("URL host must be exactly github.com")


def _require_no_credentials(username: str | None, password: str | None) -> None:
    if username is not None or password is not None:
        raise InvalidRepositoryUrlError("URL must not contain embedded credentials")


def _require_no_query_or_fragment(query: str, fragment: str) -> None:
    if query or fragment:
        raise InvalidRepositoryUrlError("URL must not contain a query or fragment")


def _parse_owner_and_repo(path: str) -> tuple[str, str]:
    match = _OWNER_REPO_PATTERN.match(path)
    if match is None:
        raise InvalidRepositoryUrlError("URL path must be /<owner>/<repo>")
    return match.group("owner"), match.group("repo")
