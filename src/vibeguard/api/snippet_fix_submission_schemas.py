"""Request and response bodies for the snippet finding fix-submission endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SnippetFixSubmissionCreateRequest(BaseModel):
    """The body of a `POST /snippets/{id}/findings/{finding_id}/fix` request."""

    fixed_content: str = Field(
        ..., description="The user's own already-fixed plain-text code for this finding"
    )


class SnippetFixSubmissionResponse(BaseModel):
    """One user-submitted fix for a snippet finding.

    Deliberately doesn't reuse the word "remediation" anywhere in this
    shape -- `SnippetFindingModel.remediation` already means
    scan-produced fix *guidance* text, a different object entirely.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    snippet_finding_id: int
    fixed_content: str
    created_at: datetime
    updated_at: datetime
