"""Tests for engine/file_preview.py -- resolving a repository's stored file and windowing it.

Deliberately never touches GitHub: this is the orchestration that
replaced RealFindingCard.tsx's old unauthenticated, per-card, direct-
to-GitHub browser fetch (Bug A). These tests exist to prove the new
backend endpoint actually serves preview content from the DB instead
of failing the way the old client-side call did.
"""

import pytest
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.core.file_preview import LineOutOfRangeError
from vibeguard.engine.file_preview import (
    FileNotFoundInRepositoryError,
    FileNotPreviewableError,
    get_file_preview,
)
from vibeguard.engine.vuln_scan import RepositoryNotFoundError


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(source_url="u", owner="octocat", name="Hello-World")
    session.add(repository)
    session.flush()
    return repository


def test_get_file_preview_returns_windowed_content_for_stored_file(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="src/app.py",
            size_bytes=100,
            content="\n".join(f"line{i}" for i in range(1, 21)),
        )
    )
    db_session.flush()

    window = get_file_preview(repository.id, "src/app.py", 10, db_session)

    assert window.highlight_line == 10
    assert [line.number for line in window.lines] == list(range(5, 16))


def test_get_file_preview_raises_for_unknown_repository(db_session: Session):
    with pytest.raises(RepositoryNotFoundError):
        get_file_preview(999, "src/app.py", 1, db_session)


def test_get_file_preview_raises_for_path_never_stored_at_intake(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id, relative_path="src/app.py", size_bytes=1, content="x"
        )
    )
    db_session.flush()

    with pytest.raises(FileNotFoundInRepositoryError):
        get_file_preview(repository.id, "src/does_not_exist.py", 1, db_session)


def test_get_file_preview_raises_for_binary_or_oversized_file_skipped_at_intake(
    db_session: Session,
):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="assets/logo.png",
            size_bytes=999_999,
            is_skipped=True,
            skip_reason="binary",
        )
    )
    db_session.flush()

    with pytest.raises(FileNotPreviewableError, match="binary"):
        get_file_preview(repository.id, "assets/logo.png", 1, db_session)


def test_get_file_preview_raises_for_line_outside_stored_file_length(db_session: Session):
    repository = _make_repository(db_session)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="src/app.py",
            size_bytes=10,
            content="one\ntwo\nthree",
        )
    )
    db_session.flush()

    with pytest.raises(LineOutOfRangeError):
        get_file_preview(repository.id, "src/app.py", 100, db_session)


def test_get_file_preview_is_scoped_to_the_requested_repository(db_session: Session):
    # Two repositories can each store a file at the same relative path
    # (the unique constraint is per-repository) -- confirm the lookup
    # doesn't leak content across repositories.
    repo_a = _make_repository(db_session)
    repo_b = RepositoryModel(source_url="u2", owner="other", name="Repo")
    db_session.add(repo_b)
    db_session.flush()
    db_session.add_all(
        [
            RepositoryFileModel(
                repository_id=repo_a.id, relative_path="app.py", size_bytes=1, content="from repo a"
            ),
            RepositoryFileModel(
                repository_id=repo_b.id, relative_path="app.py", size_bytes=1, content="from repo b"
            ),
        ]
    )
    db_session.flush()

    window = get_file_preview(repo_b.id, "app.py", 1, db_session)

    assert window.lines[0].text == "from repo b"
