"""Remediation generation, review, and approve/reject decision routes."""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.user_model import UserModel
from vibeguard.api.auth_dependencies import get_current_user
from vibeguard.api.dependencies import (
    get_db_session,
    get_github_client,
    get_llm_client,
    get_settings,
)
from vibeguard.api.remediation_schemas import (
    RemediationApproveRequest,
    RemediationGenerationResponse,
    RemediationListResponse,
    RemediationRejectRequest,
    RemediationResponse,
)
from vibeguard.engine.remediation_decision import (
    RemediationPushConflictError,
    RemediationPushPermissionDeniedError,
    RemediationPushUnavailableError,
    approve_remediation,
    reject_remediation,
)
from vibeguard.engine.remediation_generation import generate_remediations_for_repository
from vibeguard.engine.remediation_review import get_remediations_for_repository

router = APIRouter()


@router.post(
    "/repositories/{repository_id}/remediate", response_model=RemediationGenerationResponse
)
def remediate_repository(
    repository_id: int,
    current_user: UserModel = Depends(get_current_user),
    session: Session = Depends(get_db_session),
    llm_client: httpx.Client = Depends(get_llm_client),
    settings: Settings = Depends(get_settings),
) -> RemediationGenerationResponse:
    """Generate a proposed fix for every findings-bearing file in a scanned repository.

    Blocks for the whole request, same trade-off as `/scan`. 404 if the
    repository doesn't exist, 409 if it hasn't completed a scan yet.
    """
    outcome = generate_remediations_for_repository(repository_id, session, llm_client, settings)
    session.commit()
    return RemediationGenerationResponse(
        remediations=[
            RemediationResponse.model_validate(remediation)
            for remediation in outcome.remediations
        ],
        attempted=outcome.attempted,
        succeeded=outcome.succeeded,
        files_over_cap=outcome.files_over_cap,
    )


@router.get("/repositories/{repository_id}/remediations", response_model=RemediationListResponse)
def list_remediations(
    repository_id: int,
    current_user: UserModel = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> RemediationListResponse:
    """Return every remediation for a repository, newest first."""
    remediations = get_remediations_for_repository(repository_id, session)
    return RemediationListResponse(
        remediations=[RemediationResponse.model_validate(row) for row in remediations]
    )


@router.post("/remediations/{remediation_id}/approve", response_model=RemediationResponse)
def approve(
    remediation_id: int,
    body: RemediationApproveRequest,
    current_user: UserModel = Depends(get_current_user),
    session: Session = Depends(get_db_session),
    github_client: httpx.Client = Depends(get_github_client),
    settings: Settings = Depends(get_settings),
) -> RemediationResponse:
    """Approve a remediation and push it to the target GitHub repository.

    Uses the approving (authenticated) user's own stored GitHub token,
    never the original intake submitter's -- intake has no user concept
    at all. 404/409 for lookup/state errors; 403/409/502 for GitHub-side
    push failures -- see `docs/api.md` for the full status mapping.
    """
    try:
        remediation = approve_remediation(
            remediation_id, current_user, body.target_branch, session, github_client, settings
        )
    except (
        RemediationPushConflictError,
        RemediationPushPermissionDeniedError,
        RemediationPushUnavailableError,
    ):
        # The engine already recorded the push_failed outcome via
        # flush() before raising -- commit it here before propagating,
        # or `session.close()` below rolls it back and the retryable
        # push_failed state described in docs/api.md is lost.
        session.commit()
        raise
    session.commit()
    return RemediationResponse.model_validate(remediation)


@router.post("/remediations/{remediation_id}/reject", response_model=RemediationResponse)
def reject(
    remediation_id: int,
    body: RemediationRejectRequest,
    current_user: UserModel = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> RemediationResponse:
    """Reject a proposed or previously-failed remediation."""
    remediation = reject_remediation(remediation_id, current_user, body.decision_reason, session)
    session.commit()
    return RemediationResponse.model_validate(remediation)
