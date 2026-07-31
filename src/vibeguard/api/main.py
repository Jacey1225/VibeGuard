"""FastAPI application factory and lifespan wiring."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.session import build_engine, build_session_factory
from vibeguard.adapters.github.client import GitHubApiUnavailableError
from vibeguard.api.error_handlers import (
    handle_github_api_unavailable,
    handle_invalid_repository_url,
)
from vibeguard.api.routes.repositories import router as repositories_router
from vibeguard.core.github_url import InvalidRepositoryUrlError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire up shared per-process resources at startup, dispose at shutdown."""
    # database_url has no Python default -- it's supplied by the
    # VIBEGUARD_DATABASE_URL env var at runtime, which mypy can't see.
    settings = Settings()  # type: ignore[call-arg]
    engine = build_engine(settings.database_url)
    app.state.settings = settings
    app.state.session_factory = build_session_factory(engine)
    app.state.github_client = httpx.Client()
    try:
        yield
    finally:
        app.state.github_client.close()
        engine.dispose()


def create_app() -> FastAPI:
    """Build the configured FastAPI application."""
    app = FastAPI(title="VibeGuard", lifespan=lifespan)
    app.include_router(repositories_router)
    app.add_exception_handler(InvalidRepositoryUrlError, handle_invalid_repository_url)
    app.add_exception_handler(GitHubApiUnavailableError, handle_github_api_unavailable)
    return app


app = create_app()
