"""The persistence shape of a user-authored fix attached to a snippet finding.

Deliberately not `RemediationModel`: that table is repository-FK'd,
shaped around an LLM-generated proposal plus an approve/reject/push
lifecycle, and has no relationship to `SnippetFindingModel` at all. This
is new, simpler surface -- a direct `snippet_finding_id` FK (no join
table, unlike `RemediationFindingModel`), since a snippet is a single
blob with no multi-file grouping to preserve, and no status column,
since a submission either exists or it doesn't (create + read only).

`fixed_content` is deliberately not named `remediation` -- that field
already exists on `SnippetFindingModel` and means scan-produced *fix
guidance* text, not an applied fix. Reusing the name here would collide
the two meanings in the same object graph.

Cascade-deleted with its parent finding (`ondelete="CASCADE"` on
`snippet_finding_id`), which also means a submitted fix is lost when a
rescan replaces a snippet's findings (`delete_findings_for_snippet` /
`insert_snippet_findings` hard-delete and reinsert on every rescan) --
consistent with the rest of this feature area, where a rescan
invalidates anything tied to the prior finding rows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vibeguard.adapters.db.models import Base


class SnippetFixSubmissionModel(Base):
    """One user-submitted, already-fixed code blob for one snippet finding."""

    __tablename__ = "snippet_fix_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    snippet_finding_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("snippet_findings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    fixed_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
