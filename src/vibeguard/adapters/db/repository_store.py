"""Persistence operations for repository intake records."""

from sqlalchemy import insert
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.core.file_filter import SkippedFile, StoredFile
from vibeguard.core.github_url import GitHubRepoRef
from vibeguard.core.repository_status import (
    RejectionReason,
    RepositoryStatus,
    ScanFailureReason,
)


def get_repository_by_id(session: Session, repository_id: int) -> RepositoryModel | None:
    """Fetch a repository by id, or `None` if it doesn't exist."""
    return session.get(RepositoryModel, repository_id)


def insert_repository(session: Session, ref: GitHubRepoRef, source_url: str) -> RepositoryModel:
    """Create and persist a new repository intake row in `pending` status."""
    repository = RepositoryModel(
        source_url=source_url,
        owner=ref.owner,
        name=ref.repo,
        status=RepositoryStatus.PENDING,
    )
    session.add(repository)
    session.flush()
    return repository


def update_repository_status(
    session: Session,
    repository: RepositoryModel,
    status: RepositoryStatus,
    rejection_reason: RejectionReason | None = None,
) -> RepositoryModel:
    """Update a repository's status and, if rejected, its rejection reason."""
    repository.status = status
    repository.rejection_reason = rejection_reason
    session.flush()
    return repository


def bulk_insert_repository_files(
    session: Session,
    repository_id: int,
    stored: list[StoredFile],
    skipped: list[SkippedFile],
) -> None:
    """Persist every stored and skipped file for a repository in one batch.

    A single bulk `INSERT` covering all rows, not a per-file loop with
    per-row round trips (search-sort-efficiency).
    """
    rows = [
        {
            "repository_id": repository_id,
            "relative_path": file.relative_path,
            "size_bytes": file.size_bytes,
            "content": file.content,
            "is_skipped": False,
            "skip_reason": None,
        }
        for file in stored
    ] + [
        {
            "repository_id": repository_id,
            "relative_path": file.relative_path,
            "size_bytes": file.size_bytes,
            "content": None,
            "is_skipped": True,
            "skip_reason": file.skip_reason,
        }
        for file in skipped
    ]
    if rows:
        session.execute(insert(RepositoryFileModel), rows)


def update_repository_scan_outcome(
    session: Session,
    repository: RepositoryModel,
    status: RepositoryStatus,
    scan_incomplete: bool,
    scan_incomplete_reason: str | None,
    scan_failure_reason: ScanFailureReason | None,
) -> RepositoryModel:
    """Finalize a scan's outcome: status, incompleteness, and failure reason."""
    repository.status = status
    repository.scan_incomplete = scan_incomplete
    repository.scan_incomplete_reason = scan_incomplete_reason
    repository.scan_failure_reason = scan_failure_reason
    session.flush()
    return repository


def update_repository_counts(
    session: Session,
    repository: RepositoryModel,
    total_files_stored: int,
    total_files_skipped: int,
    total_bytes_stored: int,
    files_truncated: bool,
    truncation_reason: str | None,
) -> RepositoryModel:
    """Write aggregate ingest counts and truncation status onto a repository."""
    repository.total_files_stored = total_files_stored
    repository.total_files_skipped = total_files_skipped
    repository.total_bytes_stored = total_bytes_stored
    repository.files_truncated = files_truncated
    repository.truncation_reason = truncation_reason
    session.flush()
    return repository
