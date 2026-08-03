"""Top-level orchestration for a plain-text snippet submission.

Sequence: validate content is non-empty and within the per-file size
budget -> persist a row, scan-pending or rejected. The plain-text
counterpart to `engine/intake.py`, with no clone/network/file-tree step
since the content already arrived in the request body.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.adapters.db.snippet_store import insert_snippet
from vibeguard.core.file_filter import exceeds_max_file_size
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus

DEFAULT_SNIPPET_FILENAME = "pasted-snippet"


def run_snippet_intake(
    content: str, filename: str | None, session: Session, settings: Settings
) -> SnippetModel:
    """Validate and persist one submitted plain-text snippet.

    Rejects content that's empty (after stripping whitespace) or over
    the per-file size budget shared with repository intake
    (`settings.max_file_size_bytes` -- the same limit already bounding
    one repository file's content, deliberately not a separate
    setting). A too-large submission is rejected without persisting its
    content, per code-security's resource-limit rule -- only its
    measured size is kept, for diagnostics.
    """
    resolved_filename = (filename or "").strip() or DEFAULT_SNIPPET_FILENAME
    size_bytes = len(content.encode("utf-8"))

    if not content.strip():
        return insert_snippet(
            session,
            content,
            resolved_filename,
            size_bytes,
            SnippetStatus.REJECTED,
            SnippetRejectionReason.EMPTY_CONTENT,
        )

    if exceeds_max_file_size(size_bytes, settings.max_file_size_bytes):
        return insert_snippet(
            session,
            "",
            resolved_filename,
            size_bytes,
            SnippetStatus.REJECTED,
            SnippetRejectionReason.TOO_LARGE,
        )

    return insert_snippet(
        session, content, resolved_filename, size_bytes, SnippetStatus.SCAN_PENDING, None
    )
