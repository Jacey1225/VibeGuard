"""The persistence shape of a proposed code fix and its finding links.

`RemediationFindingModel` is kept in this module alongside
`RemediationModel` rather than split out: it's a join table that only
exists to record which findings one remediation addresses, the same
dependent-child relationship `RepositoryFileModel` has with
`RepositoryModel`. A join table rather than an implicit
`(repository_id, relative_path)` match because `vuln_scan.py`
hard-deletes and reinserts findings on every rescan (see
`finding_store.delete_findings_for_repository`) — matching by path
alone would silently re-associate a remediation with different findings
after a rescan, or orphan it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from vibeguard.adapters.db.enum_column import enum_values
from vibeguard.adapters.db.models import Base
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus


class RemediationModel(Base):
    """One proposed fix for a file's findings, through review and (if approved) push."""

    __tablename__ = "remediations"
    __table_args__ = (
        CheckConstraint(
            "status = 'proposed' OR decided_at IS NOT NULL",
            name="decided_at_required_once_decided",
        ),
        CheckConstraint(
            "status != 'pushed' OR pushed_commit_sha IS NOT NULL",
            name="pushed_commit_sha_required_when_pushed",
        ),
        CheckConstraint(
            "status != 'push_failed' OR push_failure_reason IS NOT NULL",
            name="push_failure_reason_required_when_push_failed",
        ),
        Index("ix_remediations_repository_id", "repository_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RemediationStatus] = mapped_column(
        Enum(RemediationStatus, name="remediation_status", values_callable=enum_values),
        nullable=False,
        default=RemediationStatus.PROPOSED,
    )
    original_content: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    diff_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    introduces_new_heuristic_hits: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    new_heuristic_hit_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    push_target_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pushed_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    push_failure_reason: Mapped[PushFailureReason | None] = mapped_column(
        Enum(PushFailureReason, name="push_failure_reason", values_callable=enum_values),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RemediationFindingModel(Base):
    """Join row recording that one remediation addresses one finding."""

    __tablename__ = "remediation_findings"
    __table_args__ = (
        UniqueConstraint("remediation_id", "finding_id", name="uq_remediation_findings_pair"),
        Index("ix_remediation_findings_remediation_id", "remediation_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    remediation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("remediations.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False
    )
