"""Request and response bodies for the repository intake/scan record."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vibeguard.core.repository_status import RejectionReason, RepositoryStatus, ScanFailureReason


class RepositorySubmitRequest(BaseModel):
    """The body of a `POST /repositories` request."""

    repo_url: str = Field(..., description="A public GitHub repository URL")


class RepositoryResponse(BaseModel):
    """The persisted state of one repository, shared by intake and scan endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_url: str
    owner: str
    name: str
    status: RepositoryStatus
    rejection_reason: RejectionReason | None
    files_truncated: bool
    truncation_reason: str | None
    total_files_stored: int
    total_files_skipped: int
    total_bytes_stored: int
    scan_incomplete: bool
    scan_incomplete_reason: str | None
    scan_failure_reason: ScanFailureReason | None
    created_at: datetime
    updated_at: datetime
