"""Tests for the full intake orchestration sequence."""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import vibeguard.engine.intake as intake_module
from tests.conftest import make_mock_github_client
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.adapters.github.clone import CloneFailedError, CloneTimeoutError
from vibeguard.core.github_url import InvalidRepositoryUrlError
from vibeguard.core.repository_status import RejectionReason, RepositoryStatus
from vibeguard.engine.intake import run_intake


def _github_client(
    *, private: bool = False, size_kb: int = 10, status_code: int = 200
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if status_code != 200:
            return httpx.Response(status_code)
        return httpx.Response(200, json={"private": private, "size": size_kb})

    return make_mock_github_client(handler)


def _redirect_clone_to(monkeypatch: pytest.MonkeyPatch, source: Path) -> None:
    real_clone_repository = intake_module.clone_repository

    def _clone_from_local_source(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        real_clone_repository(str(source), destination, timeout_seconds)

    monkeypatch.setattr(intake_module, "clone_repository", _clone_from_local_source)


def test_run_intake_malformed_url_never_persists_a_row(db_session: Session, settings_factory):
    settings = settings_factory()
    client = _github_client()

    with pytest.raises(InvalidRepositoryUrlError):
        run_intake("https://evil.example.com/o/r", db_session, client, settings)

    db_session.commit()
    assert db_session.execute(select(RepositoryModel)).scalars().all() == []


def test_run_intake_github_unavailable_raises_and_persists_no_row(
    db_session: Session, settings_factory
):
    settings = settings_factory()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    client = make_mock_github_client(handler)

    with pytest.raises(GitHubApiUnavailableError):
        run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    db_session.commit()
    assert db_session.execute(select(RepositoryModel)).scalars().all() == []


def test_run_intake_private_repo_rejects_with_a_row(db_session: Session, settings_factory):
    settings = settings_factory()
    client = _github_client(private=True)

    repository = run_intake("https://github.com/octocat/secret", db_session, client, settings)

    assert repository.status == RepositoryStatus.REJECTED
    assert repository.rejection_reason == RejectionReason.NOT_PUBLIC_OR_NOT_FOUND


def test_run_intake_not_found_repo_rejects_with_a_row(db_session: Session, settings_factory):
    settings = settings_factory()
    client = _github_client(status_code=404)

    repository = run_intake("https://github.com/octocat/nope", db_session, client, settings)

    assert repository.status == RepositoryStatus.REJECTED
    assert repository.rejection_reason == RejectionReason.NOT_PUBLIC_OR_NOT_FOUND


def test_run_intake_precheck_rejects_oversized_repo_without_cloning(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_factory(max_total_size_bytes=1000, precheck_size_fudge_factor=1.0)
    client = _github_client(size_kb=10_000)

    clone_spy = Mock()
    monkeypatch.setattr(intake_module, "clone_repository", clone_spy)

    repository = run_intake("https://github.com/octocat/huge", db_session, client, settings)

    assert repository.status == RepositoryStatus.REJECTED
    assert repository.rejection_reason == RejectionReason.REPO_TOO_LARGE
    clone_spy.assert_not_called()


def test_run_intake_happy_path_stores_files_and_marks_scan_pending(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch, local_bare_repo: Path
):
    settings = settings_factory()
    client = _github_client()
    _redirect_clone_to(monkeypatch, local_bare_repo)

    repository = run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    assert repository.status == RepositoryStatus.SCAN_PENDING_IMPLEMENTATION
    assert repository.total_files_stored == 2
    assert repository.total_files_skipped == 0
    assert repository.files_truncated is False


def test_run_intake_marks_truncated_when_file_count_limit_hit(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch, local_bare_repo: Path
):
    settings = settings_factory(max_file_count=1)
    client = _github_client()
    _redirect_clone_to(monkeypatch, local_bare_repo)

    repository = run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    assert repository.status == RepositoryStatus.SCAN_PENDING_IMPLEMENTATION
    assert repository.total_files_stored == 1
    assert repository.files_truncated is True


def test_run_intake_clone_failure_rejects(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_factory()
    client = _github_client()

    def _raise_clone_failed(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        raise CloneFailedError("simulated failure")

    monkeypatch.setattr(intake_module, "clone_repository", _raise_clone_failed)

    repository = run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    assert repository.status == RepositoryStatus.REJECTED
    assert repository.rejection_reason == RejectionReason.CLONE_FAILED


def test_run_intake_clone_timeout_rejects(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_factory()
    client = _github_client()

    def _raise_clone_timeout(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        raise CloneTimeoutError("simulated timeout")

    monkeypatch.setattr(intake_module, "clone_repository", _raise_clone_timeout)

    repository = run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    assert repository.status == RepositoryStatus.REJECTED
    assert repository.rejection_reason == RejectionReason.CLONE_TIMEOUT


def test_run_intake_removes_temp_clone_dir_even_when_clone_raises(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    settings = settings_factory()
    client = _github_client()

    clone_dir_holder: dict[str, Path] = {}
    real_create = intake_module.create_ephemeral_clone_dir

    def _tracked_create() -> Path:
        path = real_create()
        clone_dir_holder["path"] = path
        return path

    def _raise_clone_failed(clone_url: str, destination: Path, timeout_seconds: int) -> None:
        raise CloneFailedError("simulated failure")

    monkeypatch.setattr(intake_module, "create_ephemeral_clone_dir", _tracked_create)
    monkeypatch.setattr(intake_module, "clone_repository", _raise_clone_failed)

    run_intake("https://github.com/octocat/Hello-World", db_session, client, settings)

    assert not clone_dir_holder["path"].exists()
