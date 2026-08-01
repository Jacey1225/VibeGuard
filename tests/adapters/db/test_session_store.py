"""Tests for login session persistence operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from vibeguard.adapters.db.session_store import (
    delete_session,
    get_valid_session_by_token_hash,
    insert_session,
)
from vibeguard.adapters.db.user_store import upsert_user_from_github_login


def _make_user(session: Session) -> int:
    user = upsert_user_from_github_login(
        session,
        github_user_id=1,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext",
        github_oauth_token_scope="public_repo",
    )
    return user.id


def test_insert_session_persists_row(db_session: Session):
    user_id = _make_user(db_session)
    expires_at = datetime.now(UTC) + timedelta(hours=24)

    session_row = insert_session(db_session, user_id, "hash-a", expires_at)

    assert session_row.id is not None
    assert session_row.user_id == user_id
    assert session_row.token_hash == "hash-a"


def test_get_valid_session_by_token_hash_finds_unexpired_session(db_session: Session):
    user_id = _make_user(db_session)
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    insert_session(db_session, user_id, "hash-a", expires_at)

    found = get_valid_session_by_token_hash(db_session, "hash-a", datetime.now(UTC))

    assert found is not None
    assert found.token_hash == "hash-a"


def test_get_valid_session_by_token_hash_excludes_expired_session(db_session: Session):
    user_id = _make_user(db_session)
    expires_at = datetime.now(UTC) - timedelta(hours=1)
    insert_session(db_session, user_id, "hash-expired", expires_at)

    found = get_valid_session_by_token_hash(db_session, "hash-expired", datetime.now(UTC))

    assert found is None


def test_get_valid_session_by_token_hash_returns_none_for_unknown_hash(db_session: Session):
    assert get_valid_session_by_token_hash(db_session, "no-such-hash", datetime.now(UTC)) is None


def test_delete_session_revokes_it_immediately(db_session: Session):
    user_id = _make_user(db_session)
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    session_row = insert_session(db_session, user_id, "hash-a", expires_at)

    delete_session(db_session, session_row)
    db_session.flush()

    assert get_valid_session_by_token_hash(db_session, "hash-a", datetime.now(UTC)) is None
