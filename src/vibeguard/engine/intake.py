"""Top-level orchestration for a repository intake request.

Sequence: validate the URL -> check public via GitHub -> persist a row
-> pre-clone size check -> clone -> walk/filter/store files -> mark
scan-pending. Resource-limit policy: individual-file limits (oversized,
binary) always skip-and-continue; aggregate limits (file count, total
size) truncate-and-continue once real storage has started; pre-clone
conditions (bad URL, not public, GitHub-reported size over budget)
reject the whole submission since nothing expensive has happened yet.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.repository_store import (
    bulk_insert_repository_files,
    insert_repository,
    update_repository_counts,
    update_repository_status,
)
from vibeguard.adapters.filesystem.temp_dir import create_ephemeral_clone_dir, remove_clone_dir
from vibeguard.adapters.github.client import fetch_repository_metadata
from vibeguard.adapters.github.clone import CloneFailedError, CloneTimeoutError, clone_repository
from vibeguard.core.github_url import GitHubRepoRef, parse_github_repo_url
from vibeguard.core.ingest_budget import IngestBudget
from vibeguard.core.precheck import exceeds_precheck_size_budget
from vibeguard.core.repository_status import RejectionReason, RepositoryStatus
from vibeguard.engine.file_ingestion import ingest_clone_tree
from vibeguard.engine.scan_stub import mark_scan_pending_implementation


def run_intake(
    raw_url: str,
    session: Session,
    github_client: httpx.Client,
    settings: Settings,
) -> RepositoryModel:
    """Run the full intake sequence for one submitted repository URL.

    Raises:
        InvalidRepositoryUrlError: the URL isn't a valid public GitHub
            repository reference (no row is created).
        GitHubApiUnavailableError: the GitHub API itself couldn't be
            reached (no row is created).
    """
    ref = parse_github_repo_url(raw_url)
    metadata = fetch_repository_metadata(
        ref.owner, ref.repo, github_client, settings.github_api_timeout_seconds
    )

    repository = insert_repository(session, ref, raw_url)

    if not metadata.exists_and_public:
        return update_repository_status(
            session,
            repository,
            RepositoryStatus.REJECTED,
            RejectionReason.NOT_PUBLIC_OR_NOT_FOUND,
        )

    if exceeds_precheck_size_budget(
        metadata.size_kb, settings.max_total_size_bytes, settings.precheck_size_fudge_factor
    ):
        return update_repository_status(
            session, repository, RepositoryStatus.REJECTED, RejectionReason.REPO_TOO_LARGE
        )

    return _clone_and_ingest(session, repository, ref, settings)


def _clone_and_ingest(
    session: Session, repository: RepositoryModel, ref: GitHubRepoRef, settings: Settings
) -> RepositoryModel:
    clone_dir = create_ephemeral_clone_dir()
    try:
        _clone_or_reject(session, repository, ref, settings, clone_dir)
        if repository.status == RepositoryStatus.REJECTED:
            return repository
        return _ingest_and_finalize(session, repository, clone_dir, settings)
    finally:
        remove_clone_dir(clone_dir)


def _clone_or_reject(
    session: Session,
    repository: RepositoryModel,
    ref: GitHubRepoRef,
    settings: Settings,
    clone_dir: Path,
) -> None:
    try:
        clone_repository(ref.clone_url, clone_dir, settings.clone_timeout_seconds)
    except CloneTimeoutError:
        update_repository_status(
            session, repository, RepositoryStatus.REJECTED, RejectionReason.CLONE_TIMEOUT
        )
    except CloneFailedError:
        update_repository_status(
            session, repository, RepositoryStatus.REJECTED, RejectionReason.CLONE_FAILED
        )


def _ingest_and_finalize(
    session: Session, repository: RepositoryModel, clone_dir: Path, settings: Settings
) -> RepositoryModel:
    budget = IngestBudget(
        max_file_count=settings.max_file_count, max_total_bytes=settings.max_total_size_bytes
    )
    summary = ingest_clone_tree(clone_dir, settings.max_file_size_bytes, budget)
    bulk_insert_repository_files(session, repository.id, summary.stored, summary.skipped)
    update_repository_counts(
        session,
        repository,
        total_files_stored=len(summary.stored),
        total_files_skipped=len(summary.skipped),
        total_bytes_stored=budget.total_bytes,
        files_truncated=summary.files_truncated,
        truncation_reason=summary.truncation_reason,
    )
    return mark_scan_pending_implementation(session, repository)
