"""FastAPI Depends() wrappers exposing shared adapters to route handlers."""

from collections.abc import Iterator

from fastapi import Request
from httpx import Client
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.session import open_session


def get_db_session(request: Request) -> Iterator[Session]:
    """Yield a request-scoped DB session from the app's shared session factory."""
    yield from open_session(request.app.state.session_factory)


def get_github_client(request: Request) -> Client:
    """Return the app's shared httpx client for GitHub API calls."""
    client: Client = request.app.state.github_client
    return client


def get_settings(request: Request) -> Settings:
    """Return the app's loaded settings."""
    settings: Settings = request.app.state.settings
    return settings
