"""Generating and hashing opaque session tokens.

The raw token is returned to the frontend once and never stored;
only its hash is persisted (`sessions.token_hash`) — the same
principle as password hashing, so a database leak doesn't yield
directly reusable sessions.
"""

import hashlib
import secrets

_TOKEN_BYTES = 32


def generate_session_token() -> str:
    """Generate a new random, URL-safe session token."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_session_token(raw_token: str) -> str:
    """Hash a session token for storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
