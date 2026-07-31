"""Tests for parsing and validating GitHub repository URLs."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibeguard.core.github_url import (
    GitHubRepoRef,
    InvalidRepositoryUrlError,
    parse_github_repo_url,
)


@pytest.mark.parametrize(
    "raw_url,expected_owner,expected_repo",
    [
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World/", "octocat", "Hello-World"),
        ("https://github.com/o/r", "o", "r"),
        ("  https://github.com/octocat/Hello-World  ", "octocat", "Hello-World"),
    ],
)
def test_parse_github_repo_url_accepts_valid_shapes(raw_url, expected_owner, expected_repo):
    ref = parse_github_repo_url(raw_url)
    assert ref == GitHubRepoRef(owner=expected_owner, repo=expected_repo)


def test_parse_github_repo_url_builds_canonical_clone_url():
    ref = parse_github_repo_url("https://github.com/octocat/Hello-World")
    assert ref.clone_url == "https://github.com/octocat/Hello-World.git"


@pytest.mark.parametrize(
    "raw_url",
    [
        "http://github.com/octocat/Hello-World",
        "ftp://github.com/octocat/Hello-World",
    ],
)
def test_parse_github_repo_url_rejects_non_https_scheme(raw_url):
    with pytest.raises(InvalidRepositoryUrlError, match="https"):
        parse_github_repo_url(raw_url)


@pytest.mark.parametrize(
    "raw_url",
    [
        "https://notgithub.com/octocat/Hello-World",
        "https://github.com.evil.com/octocat/Hello-World",
        "https://sub.github.com/octocat/Hello-World",
        "https://192.0.2.1/octocat/Hello-World",
    ],
)
def test_parse_github_repo_url_rejects_non_github_host(raw_url):
    with pytest.raises(InvalidRepositoryUrlError, match="github.com"):
        parse_github_repo_url(raw_url)


def test_parse_github_repo_url_accepts_uppercase_host():
    ref = parse_github_repo_url("https://GITHUB.COM/octocat/Hello-World")
    assert ref == GitHubRepoRef(owner="octocat", repo="Hello-World")


def test_parse_github_repo_url_rejects_embedded_credentials():
    with pytest.raises(InvalidRepositoryUrlError, match="credentials"):
        parse_github_repo_url("https://user:pass@github.com/octocat/Hello-World")


def test_parse_github_repo_url_rejects_query_string():
    with pytest.raises(InvalidRepositoryUrlError, match="query"):
        parse_github_repo_url("https://github.com/octocat/Hello-World?tab=readme")


def test_parse_github_repo_url_rejects_fragment():
    with pytest.raises(InvalidRepositoryUrlError, match="query"):
        parse_github_repo_url("https://github.com/octocat/Hello-World#readme")


@pytest.mark.parametrize(
    "raw_url",
    [
        "https://github.com/octocat",
        "https://github.com/",
        "https://github.com/octocat/Hello-World/extra/segment",
        "https://github.com/octocat/../etc",
    ],
)
def test_parse_github_repo_url_rejects_malformed_path(raw_url):
    with pytest.raises(InvalidRepositoryUrlError):
        parse_github_repo_url(raw_url)


@given(st.text(max_size=200))
def test_parse_github_repo_url_never_raises_anything_other_than_invalid_url_error(raw_url):
    try:
        parse_github_repo_url(raw_url)
    except InvalidRepositoryUrlError:
        pass
