"""POST /repositories/{id}/scan and GET /repositories/{id}/findings."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_llm_client, get_settings
from vibeguard.api.finding_schemas import FindingListResponse, FindingResponse
from vibeguard.api.schemas import RepositoryResponse
from vibeguard.engine.vuln_scan import get_findings_for_repository, run_scan_for_repository

router = APIRouter()


@router.post("/repositories/{repository_id}/scan", response_model=RepositoryResponse)
def scan_repository(
    repository_id: int,
    session: Session = Depends(get_db_session),
    llm_client: httpx.Client = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> RepositoryResponse:
    """Run a vulnerability scan for a repository already stored via intake.

    Blocks for the whole scan — see `docs/api.md` for the known v1
    duration trade-off. 404 if the repository doesn't exist, 409 if
    it's not yet ready to scan (still cloning) or was rejected during
    intake. A second scan replaces the repository's prior findings.
    """
    repository = run_scan_for_repository(repository_id, session, llm_client, settings)
    session.commit()
    return RepositoryResponse.model_validate(repository)


@router.get("/repositories/{repository_id}/findings", response_model=FindingListResponse)
def list_findings(
    repository_id: int, session: Session = Depends(get_db_session)
) -> FindingListResponse:
    """Return every finding for a repository, worst-first."""
    findings = get_findings_for_repository(repository_id, session)
    return FindingListResponse(
        findings=[FindingResponse.model_validate(finding) for finding in findings]
    )
