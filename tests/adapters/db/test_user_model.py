"""Tests for user/session ORM model constraints against a real Postgres instance."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vibeguard.adapters.db.user_model import SessionModel, UserModel


def _make_user(session: Session, github_user_id: int = 1) -> UserModel:
    user = UserModel(
        github_user_id=github_user_id,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext",
        github_oauth_token_scope="public_repo",
    )
    session.add(user)
    session.flush()
    return user


def test_user_model_persists_with_required_fields(db_session: Session):
    user = _make_user(db_session)
    assert user.id is not None
    assert user.github_login == "octocat"


def test_users_github_user_id_unique_constraint(db_session: Session):
    _make_user(db_session, github_user_id=1)
    db_session.add(
        UserModel(
            github_user_id=1,
            github_login="someone-else",
            github_oauth_token_ciphertext="ciphertext2",
            github_oauth_token_scope="public_repo",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_session_model_cascades_on_user_delete(db_session: Session):
    user = _make_user(db_session)
    session_row = SessionModel(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(session_row)
    db_session.flush()

    session_row_id = session_row.id
    db_session.delete(user)
    db_session.flush()

    # DB-level cascade (ON DELETE CASCADE), not an ORM relationship --
    # same reasoning as RepositoryFileModel's cascade test.
    db_session.expire_all()
    assert db_session.get(SessionModel, session_row_id) is None


def test_sessions_token_hash_unique_constraint(db_session: Session):
    user = _make_user(db_session)
    db_session.add(
        SessionModel(
            user_id=user.id, token_hash="dup" * 21 + "a", expires_at=datetime.now(UTC)
        )
    )
    db_session.flush()
    db_session.add(
        SessionModel(
            user_id=user.id, token_hash="dup" * 21 + "a", expires_at=datetime.now(UTC)
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
