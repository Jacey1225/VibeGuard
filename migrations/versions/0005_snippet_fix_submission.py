"""snippet fix submissions: snippet_fix_submissions

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "snippet_fix_submissions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "snippet_finding_id",
            sa.BigInteger(),
            sa.ForeignKey("snippet_findings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("fixed_content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    # The FK's `unique=True` above already creates a unique index
    # covering lookups by snippet_finding_id -- no separate ix_ needed.


def downgrade() -> None:
    op.drop_table("snippet_fix_submissions")
