"""POST and GET /snippets/{id}/findings/{finding_id}/fix.

No `get_current_user`, no GitHub call anywhere in this module -- the
snippet path stays auth-free end to end, same as `snippets.py` and
`snippet_scans.py`.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_settings
from vibeguard.api.snippet_fix_submission_schemas import (
    SnippetFixSubmissionCreateRequest,
    SnippetFixSubmissionResponse,
)
from vibeguard.engine.snippet_fix_submission import get_snippet_fix, submit_snippet_fix

router = APIRouter()


@router.post(
    "/snippets/{snippet_id}/findings/{finding_id}/fix",
    response_model=SnippetFixSubmissionResponse,
)
def submit_fix(
    snippet_id: int,
    finding_id: int,
    body: SnippetFixSubmissionCreateRequest,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SnippetFixSubmissionResponse:
    """Attach the user's own already-fixed code to one snippet finding.

    Not an LLM-generated fix and nothing gets pushed anywhere -- this
    just records what the caller pasted. Resubmitting for the same
    finding overwrites the prior submission. 404 if the snippet or
    finding doesn't exist, 422 if `fixed_content` is empty or over the
    shared per-file size budget.
    """
    submission = submit_snippet_fix(snippet_id, finding_id, body.fixed_content, session, settings)
    session.commit()
    return SnippetFixSubmissionResponse.model_validate(submission)


@router.get(
    "/snippets/{snippet_id}/findings/{finding_id}/fix",
    response_model=SnippetFixSubmissionResponse,
)
def read_fix(
    snippet_id: int, finding_id: int, session: Session = Depends(get_db_session)
) -> SnippetFixSubmissionResponse:
    """Return the fix previously submitted for one snippet finding.

    404 if the snippet or finding doesn't exist, or if the finding
    exists but has no fix submitted yet.
    """
    submission = get_snippet_fix(snippet_id, finding_id, session)
    return SnippetFixSubmissionResponse.model_validate(submission)
