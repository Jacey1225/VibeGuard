"""Persistence operations for GitHub-authenticated user accounts."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from vibeguard.adapters.db.user_model import UserModel


def get_user_by_id(session: Session, user_id: int) -> UserModel | None:
    """Fetch a user by id, or `None` if it doesn't exist."""
    return session.get(UserModel, user_id)


def upsert_user_from_github_login(
    session: Session,
    github_user_id: int,
    github_login: str,
    github_oauth_token_ciphertext: str,
    github_oauth_token_scope: str,
) -> UserModel:
    """Create the user on first login, or refresh their login/token on every later one.

    Upserted on `github_user_id` (GitHub's stable numeric id, not the
    username, which can change) via a single `INSERT ... ON CONFLICT DO
    UPDATE` rather than a select-then-branch round trip.

    `populate_existing=True` is required: without it, a conflict path
    that hits a row already in this session's identity map returns the
    stale cached object rather than one reflecting the just-written
    values.
    """
    statement = (
        insert(UserModel)
        .values(
            github_user_id=github_user_id,
            github_login=github_login,
            github_oauth_token_ciphertext=github_oauth_token_ciphertext,
            github_oauth_token_scope=github_oauth_token_scope,
        )
        .on_conflict_do_update(
            index_elements=[UserModel.github_user_id],
            set_={
                "github_login": github_login,
                "github_oauth_token_ciphertext": github_oauth_token_ciphertext,
                "github_oauth_token_scope": github_oauth_token_scope,
            },
        )
        .returning(UserModel)
        .execution_options(populate_existing=True)
    )
    user = session.execute(statement).scalar_one()
    session.flush()
    return user
