"""Request and response bodies for the plain-text snippet intake/scan record."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vibeguard.core.repository_status import ScanFailureReason
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus


class SnippetSubmitRequest(BaseModel):
    """The body of a `POST /snippets` request."""

    content: str = Field(..., description="The plain-text source code to scan")
    filename: str | None = Field(
        None, description="Optional display name for the submitted code, shown on findings"
    )


class SnippetResponse(BaseModel):
    """The persisted state of one snippet submission, shared by intake and scan endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    size_bytes: int
    status: SnippetStatus
    rejection_reason: SnippetRejectionReason | None
    scan_incomplete: bool
    scan_incomplete_reason: str | None
    scan_failure_reason: ScanFailureReason | None
    created_at: datetime
    updated_at: datetime
