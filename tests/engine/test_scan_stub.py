"""Tests for the scan-pending placeholder hook."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.repository_store import insert_repository
from vibeguard.core.github_url import GitHubRepoRef
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.engine.scan_stub import mark_scan_pending_implementation


def test_mark_scan_pending_implementation_sets_status_only(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    updated = mark_scan_pending_implementation(db_session, repository)

    assert updated.status == RepositoryStatus.SCAN_PENDING_IMPLEMENTATION
    assert updated.rejection_reason is None
