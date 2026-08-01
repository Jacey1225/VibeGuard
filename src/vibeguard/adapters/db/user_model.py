"""The persistence shape of an authenticated GitHub user and their sessions.

`SessionModel` is kept in this module alongside `UserModel` rather than
split out: it's a dependent child table (cascade-deleted with its
parent) that only exists to carry one user's login sessions, the same
"sub-purpose the file's purpose can't be fulfilled without" case that
lets `RepositoryFileModel` share a file with `RepositoryModel`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vibeguard.adapters.db.models import Base


class UserModel(Base):
    """A user authenticated via GitHub OAuth, with their stored push credential."""

    __tablename__ = "users"
    __table_args__ = (Index("ix_users_github_user_id", "github_user_id", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    github_login: Mapped[str] = mapped_column(String(255), nullable=False)
    github_oauth_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    github_oauth_token_scope: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SessionModel(Base):
    """One issued bearer-token session for a logged-in user."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
