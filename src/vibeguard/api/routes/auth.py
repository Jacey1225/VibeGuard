"""GitHub OAuth login/callback and logout."""

import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vibeguard.adapters.auth.github_oauth_client import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_github_user,
)
from vibeguard.adapters.auth.session_token import generate_session_token, hash_session_token
from vibeguard.adapters.auth.token_cipher import encrypt_token
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.session_store import delete_session, insert_session
from vibeguard.adapters.db.user_model import SessionModel
from vibeguard.adapters.db.user_store import upsert_user_from_github_login
from vibeguard.api.auth_dependencies import UnauthenticatedError, get_current_session
from vibeguard.api.dependencies import get_db_session, get_github_client, get_settings

router = APIRouter()

_STATE_COOKIE_NAME = "vibeguard_oauth_state"


@router.get("/auth/github/login")
def start_github_login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    """Redirect the browser to GitHub's consent screen, with a CSRF `state` cookie."""
    state = secrets.token_urlsafe(32)
    redirect = RedirectResponse(
        build_authorize_url(
            settings.github_oauth_client_id, settings.github_oauth_redirect_uri, state
        )
    )
    redirect.set_cookie(
        _STATE_COOKIE_NAME,
        state,
        max_age=settings.oauth_state_cookie_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return redirect


@router.get("/auth/github/callback")
def handle_github_callback(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_db_session),
    github_client: httpx.Client = Depends(get_github_client),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Verify the OAuth state, exchange the code, and redirect with a session token.

    The `state` query param is compared to the `vibeguard_oauth_state`
    cookie before any GitHub call fires — a mismatch or missing cookie
    is rejected immediately.
    """
    cookie_state = request.cookies.get(_STATE_COOKIE_NAME)
    if cookie_state is None or cookie_state != state:
        raise UnauthenticatedError("OAuth state mismatch")

    token = exchange_code_for_token(
        code,
        settings.github_oauth_client_id,
        settings.github_oauth_client_secret,
        settings.github_oauth_redirect_uri,
        github_client,
        settings.github_api_timeout_seconds,
    )
    profile = fetch_github_user(
        token.access_token, github_client, settings.github_api_timeout_seconds
    )

    ciphertext = encrypt_token(token.access_token, settings.token_encryption_key)
    user = upsert_user_from_github_login(
        session, profile.id, profile.login, ciphertext, token.scope
    )

    raw_session_token = generate_session_token()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    insert_session(session, user.id, hash_session_token(raw_session_token), expires_at)
    session.commit()

    redirect = RedirectResponse(
        f"{settings.frontend_redirect_base_url}#session_token={raw_session_token}"
    )
    redirect.delete_cookie(_STATE_COOKIE_NAME)
    return redirect


@router.post("/auth/logout", status_code=204)
def logout(
    current_session: SessionModel = Depends(get_current_session),
    session: Session = Depends(get_db_session),
) -> None:
    """Delete the caller's session, revoking their bearer token immediately."""
    delete_session(session, current_session)
    session.commit()
