"""initial schema: repositories and repository_files

Revision ID: 0001
Revises:
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

repository_status = sa.Enum(
    "pending",
    "cloning",
    "storing",
    "scan_pending_implementation",
    "rejected",
    name="repository_status",
)
rejection_reason = sa.Enum(
    "not_public_or_not_found",
    "repo_too_large",
    "clone_failed",
    "clone_timeout",
    name="rejection_reason",
)
skip_reason = sa.Enum(
    "too_large",
    "binary",
    "file_count_limit_exceeded",
    "total_size_limit_exceeded",
    "unsafe_path",
    name="skip_reason",
)


def upgrade() -> None:
    # Each Enum is created automatically the first time it's used as a
    # column type below (op.create_table issues CREATE TYPE for it).
    op.create_table(
        "repositories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", repository_status, nullable=False, server_default="pending"),
        sa.Column("rejection_reason", rejection_reason, nullable=True),
        sa.Column("files_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("truncation_reason", sa.Text(), nullable=True),
        sa.Column("total_files_stored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_files_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes_stored", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status != 'rejected' OR rejection_reason IS NOT NULL",
            name="rejection_reason_requires_rejected_status",
        ),
    )
    op.create_index("ix_repositories_owner_name", "repositories", ["owner", "name"])

    op.create_table(
        "repository_files",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "repository_id",
            sa.BigInteger(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("skip_reason", skip_reason, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "(is_skipped = FALSE AND content IS NOT NULL AND skip_reason IS NULL) OR "
            "(is_skipped = TRUE AND content IS NULL AND skip_reason IS NOT NULL)",
            name="stored_xor_skipped",
        ),
        sa.UniqueConstraint("repository_id", "relative_path", name="uq_repository_files_path"),
    )
    op.create_index("ix_repository_files_repository_id", "repository_files", ["repository_id"])


def downgrade() -> None:
    op.drop_table("repository_files")
    op.drop_table("repositories")
    skip_reason.drop(op.get_bind(), checkfirst=True)
    rejection_reason.drop(op.get_bind(), checkfirst=True)
    repository_status.drop(op.get_bind(), checkfirst=True)
