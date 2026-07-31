"""Tests for ORM model constraints against a real Postgres instance."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.core.repository_status import RepositoryStatus, SkipReason


def test_repository_model_persists_with_defaults(db_session: Session):
    repository = RepositoryModel(source_url="https://github.com/o/r", owner="o", name="r")
    db_session.add(repository)
    db_session.flush()

    assert repository.id is not None
    assert repository.status == RepositoryStatus.PENDING
    assert repository.files_truncated is False


def test_rejection_reason_requires_rejected_status_constraint(db_session: Session):
    # Violates the constraint: status is 'rejected' but no reason is given.
    repository = RepositoryModel(
        source_url="https://github.com/o/r",
        owner="o",
        name="r",
        status=RepositoryStatus.REJECTED,
        rejection_reason=None,
    )
    db_session.add(repository)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_repository_file_stored_xor_skipped_constraint_rejects_both_set(db_session: Session):
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    db_session.add(repository)
    db_session.flush()

    bad_file = RepositoryFileModel(
        repository_id=repository.id,
        relative_path="a.py",
        size_bytes=1,
        content="x",
        is_skipped=True,
        skip_reason=SkipReason.TOO_LARGE,
    )
    db_session.add(bad_file)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_repository_file_cascades_on_repository_delete(db_session: Session):
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    db_session.add(repository)
    db_session.flush()

    file_row = RepositoryFileModel(
        repository_id=repository.id, relative_path="a.py", size_bytes=1, content="x"
    )
    db_session.add(file_row)
    db_session.flush()

    file_row_id = file_row.id
    db_session.delete(repository)
    db_session.flush()

    # The cascade happens at the DB level (ON DELETE CASCADE), not via an
    # ORM relationship, so the session's identity map won't reflect it
    # until forced to re-read from the database.
    db_session.expire_all()
    remaining = db_session.get(RepositoryFileModel, file_row_id)
    assert remaining is None


def test_repository_files_unique_path_per_repository(db_session: Session):
    repository = RepositoryModel(source_url="u", owner="o", name="r")
    db_session.add(repository)
    db_session.flush()

    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id, relative_path="a.py", size_bytes=1, content="x"
        )
    )
    db_session.flush()
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id, relative_path="a.py", size_bytes=2, content="y"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
