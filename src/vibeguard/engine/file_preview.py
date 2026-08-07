"""Orchestration for serving a finding's file preview from the repository's stored scan copy.

Deliberately never calls GitHub: the repository's files were already
read and persisted during intake (`repository_files`), so this serves
the exact content that was scanned, with no per-request GitHub
credential and no exposure to GitHub's unauthenticated rate limit.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from vibeguard.adapters.db.finding_store import get_repository_file_by_path
from vibeguard.adapters.db.repository_store import get_repository_by_id
from vibeguard.core.file_preview import FilePreviewWindow, build_preview_window
from vibeguard.core.limits import (
    DEFAULT_FILE_PREVIEW_LINES_AFTER,
    DEFAULT_FILE_PREVIEW_LINES_BEFORE,
)
from vibeguard.engine.vuln_scan import RepositoryNotFoundError

__all__ = [
    "FileNotFoundInRepositoryError",
    "FileNotPreviewableError",
    "RepositoryNotFoundError",
    "get_file_preview",
]


class FileNotFoundInRepositoryError(RuntimeError):
    """Raised when no file was stored at the requested path for this repository."""


class FileNotPreviewableError(RuntimeError):
    """Raised when the matched file has no stored content (skipped during intake)."""


def get_file_preview(
    repository_id: int,
    relative_path: str,
    line_number: int,
    session: Session,
    lines_before: int = DEFAULT_FILE_PREVIEW_LINES_BEFORE,
    lines_after: int = DEFAULT_FILE_PREVIEW_LINES_AFTER,
) -> FilePreviewWindow:
    """Look up a repository's stored file and build a windowed preview around `line_number`.

    Raises:
        RepositoryNotFoundError: no repository with this id exists.
        FileNotFoundInRepositoryError: no file was recorded at
            `relative_path` for this repository during intake.
        FileNotPreviewableError: a file was recorded at that path, but
            it was skipped during intake (binary or over a size limit)
            and has no stored content.
        LineOutOfRangeError: `line_number` is outside the file's
            current stored length (`core/file_preview.py`).
    """
    repository = get_repository_by_id(session, repository_id)
    if repository is None:
        raise RepositoryNotFoundError(f"no repository with id {repository_id}")

    file = get_repository_file_by_path(session, repository_id, relative_path)
    if file is None:
        raise FileNotFoundInRepositoryError(
            f"no file at {relative_path!r} was stored for repository {repository_id}"
        )
    if file.is_skipped or file.content is None:
        reason = file.skip_reason.value if file.skip_reason is not None else "unknown"
        raise FileNotPreviewableError(
            f"{relative_path!r} was skipped during intake ({reason}) and has no stored content"
        )

    return build_preview_window(file.content, line_number, lines_before, lines_after)
