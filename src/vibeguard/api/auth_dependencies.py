"""Resolving the authenticated user from a request's bearer token.

Bearer-in-header, not a cookie — deliberately: it's never *ambiently*
attached to cross-site requests the way a cookie is, so CSRF doesn't
apply to these routes at all. Only the pre-auth OAuth redirect leg
(`routes/auth.py`) needs its own CSRF protection, via the `state`
cookie.
"""

from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from vibeguard.adapters.auth.session_token import hash_session_token
from vibeguard.adapters.db.session_store import get_valid_session_by_token_hash
from vibeguard.adapters.db.user_model import SessionModel, UserModel
from vibeguard.adapters.db.user_store import get_user_by_id
from vibeguard.api.dependencies import get_db_session

_BEARER_PREFIX = "Bearer "


class UnauthenticatedError(RuntimeError):
    """Raised when a request's bearer token is missing, malformed, invalid, or expired."""


def get_current_session(
    request: Request, session: Session = Depends(get_db_session)
) -> SessionModel:
    """Resolve the caller's session from its `Authorization: Bearer <token>` header.

    Raises:
        UnauthenticatedError: the header is missing/malformed, or the
            token doesn't match any non-expired session.
    """
    token = _extract_bearer_token(request)
    token_hash = hash_session_token(token)
    session_row = get_valid_session_by_token_hash(session, token_hash, datetime.now(UTC))
    if session_row is None:
        raise UnauthenticatedError("session token is invalid or expired")
    return session_row


def get_current_user(
    current_session: SessionModel = Depends(get_current_session),
    session: Session = Depends(get_db_session),
) -> UserModel:
    """Resolve the caller's user account from their current session.

    Raises:
        UnauthenticatedError: propagated from `get_current_session`, or
            raised here if the session's user has since been deleted.
    """
    user = get_user_by_id(session, current_session.user_id)
    if user is None:
        raise UnauthenticatedError("session references a missing user")
    return user


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if header is None or not header.startswith(_BEARER_PREFIX):
        raise UnauthenticatedError("missing or malformed Authorization header")
    token = header[len(_BEARER_PREFIX) :].strip()
    if not token:
        raise UnauthenticatedError("missing or malformed Authorization header")
    return token
