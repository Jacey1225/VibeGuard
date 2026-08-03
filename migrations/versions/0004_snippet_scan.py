"""snippet scan pipeline: snippets, snippet_findings

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

snippet_status = sa.Enum(
    "pending",
    "scan_pending",
    "scanning",
    "scanned",
    "scan_failed",
    "rejected",
    name="snippet_status",
)
snippet_rejection_reason = sa.Enum("empty_content", "too_large", name="snippet_rejection_reason")

# Reused from migration 0002 -- these enum types already exist in the
# database. `postgresql.ENUM(..., create_type=False)` is required here
# (not the generic `sa.Enum`, whose `create_type` flag isn't honored
# through `op.create_table`'s DDL path) so this migration references
# the existing type instead of re-issuing CREATE TYPE. Symmetrically,
# downgrade doesn't drop them here -- `findings`/`repositories` still
# depend on them.
vuln_category = postgresql.ENUM(
    "injection",
    "broken_auth",
    "broken_access_control",
    "crypto_failures",
    "xxe_insecure_deserialization",
    "security_misconfiguration",
    "xss",
    "ssrf",
    "vulnerable_dependencies",
    "insufficient_logging",
    name="vuln_category",
    create_type=False,
)
severity = postgresql.ENUM(
    "info", "low", "medium", "high", "critical", name="severity", create_type=False
)
finding_source = postgresql.ENUM(
    "heuristic_only", "heuristic_confirmed", name="finding_source", create_type=False
)
scan_failure_reason = postgresql.ENUM(
    "llm_unavailable", name="scan_failure_reason", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "snippets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", snippet_status, nullable=False, server_default="pending"),
        sa.Column("rejection_reason", snippet_rejection_reason, nullable=True),
        sa.Column("scan_incomplete", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scan_incomplete_reason", sa.Text(), nullable=True),
        sa.Column("scan_failure_reason", scan_failure_reason, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status != 'rejected' OR rejection_reason IS NOT NULL",
            name="snippet_rejection_reason_requires_rejected_status",
        ),
    )

    op.create_table(
        "snippet_findings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "snippet_id",
            sa.BigInteger(),
            sa.ForeignKey("snippets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", vuln_category, nullable=False),
        sa.Column("severity", severity, nullable=False),
        sa.Column("source", finding_source, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_snippet_findings_snippet_id", "snippet_findings", ["snippet_id"])


def downgrade() -> None:
    op.drop_index("ix_snippet_findings_snippet_id", table_name="snippet_findings")
    op.drop_table("snippet_findings")
    op.drop_table("snippets")
    snippet_rejection_reason.drop(op.get_bind(), checkfirst=True)
    snippet_status.drop(op.get_bind(), checkfirst=True)
