"""Tests for repository intake persistence operations."""

from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryFileModel
from vibeguard.adapters.db.repository_store import (
    bulk_insert_repository_files,
    insert_repository,
    update_repository_counts,
    update_repository_status,
)
from vibeguard.core.file_filter import SkippedFile, StoredFile
from vibeguard.core.github_url import GitHubRepoRef
from vibeguard.core.repository_status import RejectionReason, RepositoryStatus, SkipReason


def test_insert_repository_creates_pending_row(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    assert repository.id is not None
    assert repository.owner == "octocat"
    assert repository.name == "Hello-World"
    assert repository.status == RepositoryStatus.PENDING


def test_update_repository_status_sets_status_and_rejection_reason(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    updated = update_repository_status(
        db_session, repository, RepositoryStatus.REJECTED, RejectionReason.NOT_PUBLIC_OR_NOT_FOUND
    )

    assert updated.status == RepositoryStatus.REJECTED
    assert updated.rejection_reason == RejectionReason.NOT_PUBLIC_OR_NOT_FOUND


def test_bulk_insert_repository_files_persists_stored_and_skipped_rows(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    stored = [StoredFile("a.py", 10, "print(1)"), StoredFile("b.py", 12, "print(2)")]
    skipped = [SkippedFile("big.bin", 9_999, SkipReason.TOO_LARGE)]

    bulk_insert_repository_files(db_session, repository.id, stored, skipped)
    db_session.flush()

    rows = db_session.execute(
        select(RepositoryFileModel).where(RepositoryFileModel.repository_id == repository.id)
    ).scalars().all()
    assert len(rows) == 3
    assert {row.relative_path for row in rows} == {"a.py", "b.py", "big.bin"}
    skipped_row = next(row for row in rows if row.relative_path == "big.bin")
    assert skipped_row.is_skipped is True
    assert skipped_row.skip_reason == SkipReason.TOO_LARGE
    assert skipped_row.content is None


def test_bulk_insert_repository_files_with_no_rows_is_a_no_op(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    bulk_insert_repository_files(db_session, repository.id, [], [])
    db_session.flush()

    rows = db_session.execute(
        select(RepositoryFileModel).where(RepositoryFileModel.repository_id == repository.id)
    ).scalars().all()
    assert rows == []


def test_bulk_insert_repository_files_executes_a_single_round_trip(
    db_session: Session, db_engine: Engine
):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")
    db_session.flush()

    stored = [StoredFile(f"file{i}.py", 10, "x") for i in range(50)]

    statement_count = 0

    def _count_statements(*args: object, **kwargs: object) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(db_engine, "before_cursor_execute", _count_statements)
    try:
        bulk_insert_repository_files(db_session, repository.id, stored, [])
    finally:
        event.remove(db_engine, "before_cursor_execute", _count_statements)

    assert statement_count == 1


def test_update_repository_counts_writes_aggregate_fields(db_session: Session):
    ref = GitHubRepoRef(owner="octocat", repo="Hello-World")
    repository = insert_repository(db_session, ref, "https://github.com/octocat/Hello-World")

    updated = update_repository_counts(
        db_session,
        repository,
        total_files_stored=10,
        total_files_skipped=2,
        total_bytes_stored=1234,
        files_truncated=True,
        truncation_reason="file_count_limit_exceeded",
    )

    assert updated.total_files_stored == 10
    assert updated.total_files_skipped == 2
    assert updated.total_bytes_stored == 1234
    assert updated.files_truncated is True
    assert updated.truncation_reason == "file_count_limit_exceeded"
