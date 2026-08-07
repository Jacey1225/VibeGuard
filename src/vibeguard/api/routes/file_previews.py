"""GET /repositories/{id}/files/preview -- a finding's windowed file preview."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from vibeguard.api.dependencies import get_db_session
from vibeguard.api.file_preview_schemas import FilePreviewResponse, PreviewLineResponse
from vibeguard.engine.file_preview import get_file_preview

router = APIRouter()


@router.get("/repositories/{repository_id}/files/preview", response_model=FilePreviewResponse)
def preview_file(
    repository_id: int,
    path: str = Query(..., description="A finding's relative_path within the repository"),
    line: int = Query(..., ge=1, description="A finding's reported line number, 1-indexed"),
    session: Session = Depends(get_db_session),
) -> FilePreviewResponse:
    """Return a windowed, line-numbered preview of a stored file, centered on `line`.

    Served entirely from the repository's already-cloned scan copy
    (`repository_files`, populated during intake) -- never a live call
    to GitHub -- so the preview can't drift from what was actually
    scanned and needs no per-request GitHub credential from the caller.
    No auth required, matching `GET .../findings`: this is exactly the
    content public intake already stored, not user-scoped data. 404 if
    the repository or file path doesn't exist; 422 if the file was
    skipped during intake (binary/oversized) or `line` is outside the
    file's current stored length -- see `docs/api.md` for the full
    status mapping.
    """
    window = get_file_preview(repository_id, path, line, session)
    return FilePreviewResponse(
        relative_path=path,
        lines=[PreviewLineResponse(number=item.number, text=item.text) for item in window.lines],
        highlight_line=window.highlight_line,
    )
