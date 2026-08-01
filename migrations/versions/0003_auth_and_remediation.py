"""auth and remediation: users, sessions, remediations, remediation_findings

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

remediation_status = sa.Enum(
    "proposed", "rejected", "pushed", "push_failed", name="remediation_status"
)
push_failure_reason = sa.Enum(
    "stale_sha_conflict",
    "github_api_unavailable",
    "github_permission_denied",
    name="push_failure_reason",
)


def upgrade() -> None:
    # Every enum here is only ever used by create_table below, so each
    # is auto-created the first time it's referenced -- unlike 0002's
    # repository_status swap, nothing here ALTERs an existing enum
    # column, so none of that migration's OID/CHECK-constraint gotchas
    # apply.
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_user_id", sa.BigInteger(), nullable=False),
        sa.Column("github_login", sa.String(length=255), nullable=False),
        sa.Column("github_oauth_token_ciphertext", sa.Text(), nullable=False),
        sa.Column("github_oauth_token_scope", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_github_user_id", "users", ["github_user_id"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "remediations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "repository_id",
            sa.BigInteger(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column(
            "status", remediation_status, nullable=False, server_default="proposed"
        ),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "introduces_new_heuristic_hits",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("new_heuristic_hit_summary", sa.Text(), nullable=True),
        sa.Column("push_target_branch", sa.String(length=255), nullable=True),
        sa.Column("pushed_commit_sha", sa.String(length=64), nullable=True),
        sa.Column("push_failure_reason", push_failure_reason, nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "decided_by_user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status = 'proposed' OR decided_at IS NOT NULL",
            name="decided_at_required_once_decided",
        ),
        sa.CheckConstraint(
            "status != 'pushed' OR pushed_commit_sha IS NOT NULL",
            name="pushed_commit_sha_required_when_pushed",
        ),
        sa.CheckConstraint(
            "status != 'push_failed' OR push_failure_reason IS NOT NULL",
            name="push_failure_reason_required_when_push_failed",
        ),
    )
    op.create_index("ix_remediations_repository_id", "remediations", ["repository_id"])

    op.create_table(
        "remediation_findings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "remediation_id",
            sa.BigInteger(),
            sa.ForeignKey("remediations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.BigInteger(),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("remediation_id", "finding_id", name="uq_remediation_findings_pair"),
    )
    op.create_index(
        "ix_remediation_findings_remediation_id", "remediation_findings", ["remediation_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_remediation_findings_remediation_id", table_name="remediation_findings"
    )
    op.drop_table("remediation_findings")

    op.drop_index("ix_remediations_repository_id", table_name="remediations")
    op.drop_table("remediations")
    push_failure_reason.drop(op.get_bind(), checkfirst=True)
    remediation_status.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_token_hash", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_users_github_user_id", table_name="users")
    op.drop_table("users")
