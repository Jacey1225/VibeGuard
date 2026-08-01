"""Persistence operations for login sessions."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vibeguard.adapters.db.user_model import SessionModel


def insert_session(
    session: Session, user_id: int, token_hash: str, expires_at: datetime
) -> SessionModel:
    """Create and persist a new session row for a just-authenticated user."""
    session_row = SessionModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(session_row)
    session.flush()
    return session_row


def get_valid_session_by_token_hash(
    session: Session, token_hash: str, now: datetime
) -> SessionModel | None:
    """Fetch a non-expired session by its token's hash, or `None` if absent/expired."""
    statement = select(SessionModel).where(
        SessionModel.token_hash == token_hash,
        SessionModel.expires_at > now,
    )
    return session.execute(statement).scalar_one_or_none()


def delete_session(session: Session, session_row: SessionModel) -> None:
    """Delete a session row, revoking that bearer token immediately."""
    session.execute(delete(SessionModel).where(SessionModel.id == session_row.id))
