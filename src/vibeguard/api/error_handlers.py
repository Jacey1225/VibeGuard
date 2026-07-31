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
