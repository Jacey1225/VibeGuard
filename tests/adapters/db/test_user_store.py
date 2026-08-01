"""Tests for GitHub-authenticated user persistence operations."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.user_store import get_user_by_id, upsert_user_from_github_login


def test_upsert_user_from_github_login_creates_new_user(db_session: Session):
    user = upsert_user_from_github_login(
        db_session,
        github_user_id=42,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext-a",
        github_oauth_token_scope="public_repo",
    )

    assert user.id is not None
    assert user.github_user_id == 42
    assert user.github_login == "octocat"
    assert user.github_oauth_token_ciphertext == "ciphertext-a"


def test_upsert_user_from_github_login_updates_existing_user_on_relogin(db_session: Session):
    first = upsert_user_from_github_login(
        db_session,
        github_user_id=42,
        github_login="octocat",
        github_oauth_token_ciphertext="ciphertext-a",
        github_oauth_token_scope="public_repo",
    )

    second = upsert_user_from_github_login(
        db_session,
        github_user_id=42,
        github_login="octocat-renamed",
        github_oauth_token_ciphertext="ciphertext-b",
        github_oauth_token_scope="public_repo",
    )

    assert second.id == first.id
    assert second.github_login == "octocat-renamed"
    assert second.github_oauth_token_ciphertext == "ciphertext-b"


def test_get_user_by_id_returns_none_for_missing_user(db_session: Session):
    assert get_user_by_id(db_session, 999_999) is None
