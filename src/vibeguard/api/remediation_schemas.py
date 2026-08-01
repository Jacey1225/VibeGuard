"""Request and response bodies for the remediation generation/review/decision endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus


class RemediationResponse(BaseModel):
    """One proposed fix, through review and (if approved) push."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    relative_path: str
    status: RemediationStatus
    original_content: str
    proposed_content: str
    diff_text: str
    summary: str
    model: str
    introduces_new_heuristic_hits: bool
    new_heuristic_hit_summary: str | None
    push_target_branch: str | None
    pushed_commit_sha: str | None
    push_failure_reason: PushFailureReason | None
    decided_at: datetime | None
    decided_by_user_id: int | None
    decision_reason: str | None
    created_at: datetime


class RemediationListResponse(BaseModel):
    """Every remediation for one repository, newest first."""

    remediations: list[RemediationResponse]


class RemediationGenerationResponse(BaseModel):
    """The outcome of one `POST /repositories/{id}/remediate` call."""

    remediations: list[RemediationResponse]
    attempted: int
    succeeded: int
    files_over_cap: int


class RemediationApproveRequest(BaseModel):
    """The body of a `POST /remediations/{id}/approve` request."""

    target_branch: str | None = None


class RemediationRejectRequest(BaseModel):
    """The body of a `POST /remediations/{id}/reject` request."""

    decision_reason: str | None = None
