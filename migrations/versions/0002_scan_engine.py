"""scan engine: findings table, extended repository status, scan incomplete/failure columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_REPOSITORY_STATUS_VALUES = (
    "pending",
    "cloning",
    "storing",
    "scan_pending_implementation",
    "rejected",
)
_NEW_REPOSITORY_STATUS_VALUES = (
    "pending",
    "cloning",
    "storing",
    "scan_pending_implementation",
    "scanning",
    "scanned",
    "scan_failed",
    "rejected",
)

scan_failure_reason = sa.Enum("llm_unavailable", name="scan_failure_reason")
vuln_category = sa.Enum(
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
)
severity = sa.Enum("info", "low", "medium", "high", "critical", name="severity")
finding_source = sa.Enum("heuristic_only", "heuristic_confirmed", name="finding_source")


def _recreate_repository_status_enum(new_values: tuple[str, ...]) -> None:
    """Swap the `repository_status` type to `new_values`, preserving existing data.

    Postgres has no `ALTER TYPE ... DROP VALUE`, so changing an enum's
    value set safely -- and symmetrically, so downgrade can undo it --
    means recreating the type rather than `ADD VALUE`.
    """
    bind = op.get_bind()
    # Both the column's server_default ('pending') and the CHECK
    # constraint referencing the 'rejected' enum literal are bound to
    # the old type's OID and block the ALTER COLUMN TYPE below --
    # both come off before the swap and go back on after.
    op.execute(
        "ALTER TABLE repositories DROP CONSTRAINT rejection_reason_requires_rejected_status"
    )
    op.execute("ALTER TABLE repositories ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE repository_status RENAME TO repository_status_old")
    new_type = sa.Enum(*new_values, name="repository_status")
    new_type.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE repositories ALTER COLUMN status TYPE repository_status "
        "USING status::text::repository_status"
    )
    op.execute("DROP TYPE repository_status_old")
    op.execute("ALTER TABLE repositories ALTER COLUMN status SET DEFAULT 'pending'")
    op.execute(
        "ALTER TABLE repositories ADD CONSTRAINT rejection_reason_requires_rejected_status "
        "CHECK (status != 'rejected' OR rejection_reason IS NOT NULL)"
    )


def upgrade() -> None:
    _recreate_repository_status_enum(_NEW_REPOSITORY_STATUS_VALUES)

    bind = op.get_bind()
    # Used via add_column (not create_table), so it needs an explicit
    # create -- add_column doesn't dispatch the auto-create-on-table-
    # create event create_table relies on for vuln_category/severity/
    # finding_source below.
    scan_failure_reason.create(bind, checkfirst=True)

    op.add_column(
        "repositories",
        sa.Column("scan_incomplete", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("repositories", sa.Column("scan_incomplete_reason", sa.Text(), nullable=True))
    op.add_column(
        "repositories", sa.Column("scan_failure_reason", scan_failure_reason, nullable=True)
    )

    op.create_table(
        "findings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "repository_id",
            sa.BigInteger(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
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
    op.create_index("ix_findings_repository_id", "findings", ["repository_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_repository_id", table_name="findings")
    op.drop_table("findings")
    finding_source.drop(op.get_bind(), checkfirst=True)
    severity.drop(op.get_bind(), checkfirst=True)
    vuln_category.drop(op.get_bind(), checkfirst=True)

    op.drop_column("repositories", "scan_failure_reason")
    op.drop_column("repositories", "scan_incomplete_reason")
    op.drop_column("repositories", "scan_incomplete")
    scan_failure_reason.drop(op.get_bind(), checkfirst=True)

    # This cast fails if any row currently has a status value outside
    # the original 5 (scanning/scanned/scan_failed) -- downgrading past
    # this migration is only safe before any scan has ever run.
    _recreate_repository_status_enum(_OLD_REPOSITORY_STATUS_VALUES)
