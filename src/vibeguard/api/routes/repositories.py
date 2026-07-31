"""POST /repositories — submit a public GitHub repository for scanning."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_github_client, get_settings
from vibeguard.api.schemas import RepositoryResponse, RepositorySubmitRequest
from vibeguard.engine.intake import run_intake

router = APIRouter()


@router.post("/repositories", response_model=RepositoryResponse, status_code=201)
def submit_repository(
    body: RepositorySubmitRequest,
    session: Session = Depends(get_db_session),
    github_client: httpx.Client = Depends(get_github_client),
    settings: Settings = Depends(get_settings),
) -> RepositoryResponse:
    """Validate, clone, and store a public GitHub repository, then return it.

    Blocks for the whole request — no background job queue. A row is
    only ever created once the GitHub API has answered about this
    specific repository; a malformed URL or an unreachable GitHub API
    never persists anything (see the exception handlers registered in
    `api.main` for their HTTP status mapping).
    """
    repository = run_intake(body.repo_url, session, github_client, settings)
    session.commit()
    return RepositoryResponse.model_validate(repository)
