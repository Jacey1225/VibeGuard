"""FastAPI application factory and lifespan wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from vibeguard.adapters.auth.github_oauth_client import (
    GitHubOAuthResponseParseError,
    GitHubOAuthUnavailableError,
)
from vibeguard.adapters.config.settings import Settings, load_cors_allowed_origins
from vibeguard.adapters.db.session import build_engine, build_session_factory
from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.api.auth_dependencies import UnauthenticatedError
from vibeguard.api.error_handlers import (
    handle_github_api_unavailable,
    handle_github_oauth_login_failed,
    handle_github_oauth_unavailable,
    handle_invalid_repository_url,
    handle_remediation_already_decided,
    handle_remediation_not_found,
    handle_remediation_push_conflict,
    handle_remediation_push_permission_denied,
    handle_remediation_push_unavailable,
    handle_repository_not_found,
    handle_repository_not_ready_for_remediation,
    handle_repository_not_ready_for_scan,
    handle_snippet_not_found,
    handle_snippet_not_ready_for_scan,
    handle_unauthenticated,
)
from vibeguard.api.routes.auth import router as auth_router
from vibeguard.api.routes.remediations import router as remediations_router
from vibeguard.api.routes.repositories import router as repositories_router
from vibeguard.api.routes.scans import router as scans_router
from vibeguard.api.routes.snippet_scans import router as snippet_scans_router
from vibeguard.api.routes.snippets import router as snippets_router
from vibeguard.core.github_url import InvalidRepositoryUrlError
from vibeguard.engine.remediation_decision import (
    RemediationAlreadyDecidedError,
    RemediationNotFoundError,
    RemediationPushConflictError,
    RemediationPushPermissionDeniedError,
    RemediationPushUnavailableError,
)
from vibeguard.engine.remediation_generation import RepositoryNotReadyForRemediationError
from vibeguard.engine.snippet_scan import SnippetNotFoundError, SnippetNotReadyForScanError
from vibeguard.engine.vuln_scan import RepositoryNotFoundError, RepositoryNotReadyForScanError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire up shared per-process resources at startup, dispose at shutdown."""
    # database_url and openrouter_api_key have no Python defaults --
    # they're supplied by env vars at runtime, which mypy can't see.
    settings = Settings()  # type: ignore[call-arg]
    engine = build_engine(settings.database_url)
    app.state.settings = settings
    app.state.session_factory = build_session_factory(engine)
    app.state.github_client = httpx.Client()
    app.state.llm_client = httpx.Client()
    try:
        yield
    finally:
        app.state.github_client.close()
        app.state.llm_client.close()
        engine.dispose()


def create_app() -> FastAPI:
    """Build the configured FastAPI application."""
    app = FastAPI(title="VibeGuard", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=load_cors_allowed_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(repositories_router)
    app.include_router(scans_router)
    app.include_router(auth_router)
    app.include_router(remediations_router)
    app.include_router(snippets_router)
    app.include_router(snippet_scans_router)
    app.add_exception_handler(InvalidRepositoryUrlError, handle_invalid_repository_url)
    app.add_exception_handler(GitHubApiUnavailableError, handle_github_api_unavailable)
    app.add_exception_handler(RepositoryNotFoundError, handle_repository_not_found)
    app.add_exception_handler(RepositoryNotReadyForScanError, handle_repository_not_ready_for_scan)
    app.add_exception_handler(
        RepositoryNotReadyForRemediationError, handle_repository_not_ready_for_remediation
    )
    app.add_exception_handler(SnippetNotFoundError, handle_snippet_not_found)
    app.add_exception_handler(SnippetNotReadyForScanError, handle_snippet_not_ready_for_scan)
    app.add_exception_handler(UnauthenticatedError, handle_unauthenticated)
    app.add_exception_handler(GitHubOAuthUnavailableError, handle_github_oauth_unavailable)
    app.add_exception_handler(GitHubOAuthResponseParseError, handle_github_oauth_login_failed)
    app.add_exception_handler(RemediationNotFoundError, handle_remediation_not_found)
    app.add_exception_handler(RemediationAlreadyDecidedError, handle_remediation_already_decided)
    app.add_exception_handler(RemediationPushConflictError, handle_remediation_push_conflict)
    app.add_exception_handler(
        RemediationPushPermissionDeniedError, handle_remediation_push_permission_denied
    )
    app.add_exception_handler(RemediationPushUnavailableError, handle_remediation_push_unavailable)
    return app


app = create_app()
