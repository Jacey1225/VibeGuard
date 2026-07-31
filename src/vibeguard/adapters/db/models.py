"""The persistence shape of a repository intake attempt and its files.

`RepositoryFileModel` is kept in this module alongside `RepositoryModel`
rather than split out: it's a dependent child table (cascade-deleted
with its parent) that only exists to carry one repository's file
contents, which is exactly the "sub-purpose the file's purpose can't be
fulfilled without" case the single-purpose-cascade rule allows.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from vibeguard.core.repository_status import RejectionReason, RepositoryStatus, SkipReason


class Base(DeclarativeBase):
    """Shared declarative base for all VibeGuard ORM models."""


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class RepositoryModel(Base):
    """One repository intake attempt: a submitted URL and its outcome."""

    __tablename__ = "repositories"
    __table_args__ = (
        CheckConstraint(
            "status != 'rejected' OR rejection_reason IS NOT NULL",
            name="rejection_reason_requires_rejected_status",
        ),
        Index("ix_repositories_owner_name", "owner", "name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(RepositoryStatus, name="repository_status", values_callable=_enum_values),
        nullable=False,
        default=RepositoryStatus.PENDING,
    )
    rejection_reason: Mapped[RejectionReason | None] = mapped_column(
        Enum(RejectionReason, name="rejection_reason", values_callable=_enum_values),
        nullable=True,
    )
    files_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    truncation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_files_stored: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_files_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes_stored: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RepositoryFileModel(Base):
    """One file's outcome (stored or skipped) within a repository intake."""

    __tablename__ = "repository_files"
    __table_args__ = (
        CheckConstraint(
            "(is_skipped = FALSE AND content IS NOT NULL AND skip_reason IS NULL) OR "
            "(is_skipped = TRUE AND content IS NULL AND skip_reason IS NOT NULL)",
            name="stored_xor_skipped",
        ),
        UniqueConstraint("repository_id", "relative_path", name="uq_repository_files_path"),
        Index("ix_repository_files_repository_id", "repository_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    skip_reason: Mapped[SkipReason | None] = mapped_column(
        Enum(SkipReason, name="skip_reason", values_callable=_enum_values),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
