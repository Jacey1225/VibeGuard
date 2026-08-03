"""The persistence shape of one plain-text code snippet scan attempt."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vibeguard.adapters.db.enum_column import enum_values
from vibeguard.adapters.db.models import Base
from vibeguard.core.repository_status import ScanFailureReason
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus


class SnippetModel(Base):
    """One plain-text code submission and its scan outcome.

    The plain-text counterpart to `RepositoryModel`: a single blob of
    submitted content rather than a cloned file tree, so there's no
    dependent child-file table -- `content` is stored directly on this
    row.
    """

    __tablename__ = "snippets"
    __table_args__ = (
        CheckConstraint(
            "status != 'rejected' OR rejection_reason IS NOT NULL",
            name="snippet_rejection_reason_requires_rejected_status",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SnippetStatus] = mapped_column(
        Enum(SnippetStatus, name="snippet_status", values_callable=enum_values),
        nullable=False,
        default=SnippetStatus.PENDING,
    )
    rejection_reason: Mapped[SnippetRejectionReason | None] = mapped_column(
        Enum(
            SnippetRejectionReason,
            name="snippet_rejection_reason",
            values_callable=enum_values,
        ),
        nullable=True,
    )
    scan_incomplete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scan_incomplete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    scan_failure_reason: Mapped[ScanFailureReason | None] = mapped_column(
        Enum(ScanFailureReason, name="scan_failure_reason", values_callable=enum_values),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
