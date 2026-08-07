"""Mapping engine/adapter exceptions to HTTP responses.

No internal detail (stack traces, exception internals) is returned to
the client for infra-level failures — only a client-safe message.

Handlers are typed against the base `Exception`, matching Starlette's
`add_exception_handler` contract exactly (it dispatches by the
registered exception type, so each handler only ever actually receives
an instance of the type it was registered for in `api.main`).
"""

from fastapi import Request
from fastapi.responses import JSONResponse


async def handle_invalid_repository_url(request: Request, exc: Exception) -> JSONResponse:
    """Return 422 for a malformed or non-github repository URL."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def handle_github_api_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Return 502 when the GitHub API itself couldn't be reached."""
    return JSONResponse(status_code=502, content={"detail": "GitHub API unavailable, try again"})


async def handle_repository_not_found(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when the requested repository id doesn't exist."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_repository_not_ready_for_scan(request: Request, exc: Exception) -> JSONResponse:
    """Return 409 when the repository isn't in a status that allows scanning."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def handle_repository_not_ready_for_remediation(
    request: Request, exc: Exception
) -> JSONResponse:
    """Return 409 when the repository hasn't completed a scan yet."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def handle_snippet_not_found(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when the requested snippet id doesn't exist."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_snippet_not_ready_for_scan(request: Request, exc: Exception) -> JSONResponse:
    """Return 409 when the snippet isn't in a status that allows scanning."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def handle_snippet_finding_not_found(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when the requested finding id doesn't exist for this snippet."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_snippet_fix_submission_not_found(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when the finding exists but has no fix submitted yet."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_snippet_fix_content_invalid(request: Request, exc: Exception) -> JSONResponse:
    """Return 422 when submitted fix content is empty or over the size budget."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def handle_unauthenticated(request: Request, exc: Exception) -> JSONResponse:
    """Return 401 when a request's bearer token is missing, invalid, or expired."""
    return JSONResponse(status_code=401, content={"detail": str(exc)})


async def handle_github_oauth_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Return 502 when GitHub's OAuth endpoints couldn't be reached."""
    return JSONResponse(status_code=502, content={"detail": "GitHub OAuth unavailable, try again"})


async def handle_github_oauth_login_failed(request: Request, exc: Exception) -> JSONResponse:
    """Return 401 when GitHub rejected the OAuth code or returned an unparseable response."""
    return JSONResponse(status_code=401, content={"detail": "GitHub login failed"})


async def handle_remediation_not_found(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when the requested remediation id doesn't exist."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_remediation_already_decided(request: Request, exc: Exception) -> JSONResponse:
    """Return 409 when a remediation has already reached a terminal decision."""
    return JSONResponse(status_code=409, content={"detail": str(exc)})


async def handle_remediation_push_conflict(request: Request, exc: Exception) -> JSONResponse:
    """Return 409 when the target file changed upstream since the proposal was generated."""
    return JSONResponse(
        status_code=409,
        content={
            "detail": "the target file has changed on GitHub since this fix was generated; "
            "regenerate the remediation and try again"
        },
    )


async def handle_remediation_push_permission_denied(
    request: Request, exc: Exception
) -> JSONResponse:
    """Return 403 when the approving user's token can't write to the target repository."""
    return JSONResponse(status_code=403, content={"detail": str(exc)})


async def handle_remediation_push_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """Return 502 when GitHub's API couldn't be reached or failed unexpectedly during a push."""
    return JSONResponse(status_code=502, content={"detail": "GitHub API unavailable, try again"})


async def handle_file_not_found_in_repository(request: Request, exc: Exception) -> JSONResponse:
    """Return 404 when no file was stored at the requested path for this repository."""
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def handle_file_not_previewable(request: Request, exc: Exception) -> JSONResponse:
    """Return 422 when the matched file has no stored content (skipped during intake)."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def handle_line_out_of_range(request: Request, exc: Exception) -> JSONResponse:
    """Return 422 when the requested line number is outside the file's current stored length."""
    return JSONResponse(status_code=422, content={"detail": str(exc)})
