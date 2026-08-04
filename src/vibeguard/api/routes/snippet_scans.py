"""POST /snippets/{id}/scan and GET /snippets/{id}/findings."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_llm_client, get_settings
from vibeguard.api.finding_schemas import FindingListResponse, FindingResponse
from vibeguard.api.scan_schemas import ScanRequest
from vibeguard.api.snippet_schemas import SnippetResponse
from vibeguard.engine.snippet_scan import get_findings_for_snippet, run_snippet_scan_for_id

router = APIRouter()


@router.post("/snippets/{snippet_id}/scan", response_model=SnippetResponse)
def scan_snippet(
    snippet_id: int,
    body: ScanRequest | None = None,
    session: Session = Depends(get_db_session),
    llm_client: httpx.Client = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> SnippetResponse:
    """Run a vulnerability scan for a snippet already stored via intake.

    Blocks for the whole scan, the same trade-off `POST
    /repositories/{id}/scan` makes. 404 if the snippet doesn't exist,
    409 if it was rejected during intake. A second scan replaces the
    snippet's prior findings. The optional request body's `categories`
    field selects which vulnerability categories to scan for — omit it
    (or the whole body) to scan every category, same as before this
    field existed.
    """
    selected_categories = body.selected_categories() if body is not None else None
    snippet = run_snippet_scan_for_id(
        snippet_id, session, llm_client, settings, selected_categories
    )
    session.commit()
    return SnippetResponse.model_validate(snippet)


@router.get("/snippets/{snippet_id}/findings", response_model=FindingListResponse)
def list_snippet_findings(
    snippet_id: int, session: Session = Depends(get_db_session)
) -> FindingListResponse:
    """Return every finding for a snippet, worst-first."""
    findings = get_findings_for_snippet(snippet_id, session)
    return FindingListResponse(
        findings=[FindingResponse.model_validate(finding) for finding in findings]
    )
