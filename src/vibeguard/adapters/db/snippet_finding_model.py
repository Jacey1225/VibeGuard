"""The persistence shape of one vulnerability finding within a snippet scan.

A dependent child table of `snippets` (cascade-deleted with its parent),
the plain-text counterpart to `FindingModel` -- kept as its own table
rather than a nullable second foreign key on `findings` so neither
table has to account for a parent type it doesn't apply to.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vibeguard.adapters.db.enum_column import enum_values
from vibeguard.adapters.db.models import Base
from vibeguard.core.finding import FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


class SnippetFindingModel(Base):
    """One confirmed vulnerability finding within a plain-text snippet scan."""

    __tablename__ = "snippet_findings"
    __table_args__ = (Index("ix_snippet_findings_snippet_id", "snippet_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snippet_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("snippets.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[VulnCategory] = mapped_column(
        Enum(VulnCategory, name="vuln_category", values_callable=enum_values), nullable=False
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity", values_callable=enum_values), nullable=False
    )
    source: Mapped[FindingSource] = mapped_column(
        Enum(FindingSource, name="finding_source", values_callable=enum_values), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
