"""POST /snippets -- submit plain-text code for scanning."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_settings
from vibeguard.api.snippet_schemas import SnippetResponse, SnippetSubmitRequest
from vibeguard.engine.snippet_intake import run_snippet_intake

router = APIRouter()


@router.post("/snippets", response_model=SnippetResponse, status_code=201)
def submit_snippet(
    body: SnippetSubmitRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SnippetResponse:
    """Validate and store submitted plain-text code, then return it.

    Always returns `201` -- unlike repository intake there's no external
    service to fail against, so the only outcomes are `scan_pending`
    (ready to scan) or `rejected` (empty or over the size budget shared
    with repository file intake; see `docs/api.md`).
    """
    snippet = run_snippet_intake(body.content, body.filename, session, settings)
    session.commit()
    return SnippetResponse.model_validate(snippet)
