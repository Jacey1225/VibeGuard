"""Tests for session token generation and hashing."""

from vibeguard.adapters.auth.session_token import generate_session_token, hash_session_token


def test_generate_session_token_is_reasonably_long_and_url_safe():
    token = generate_session_token()
    assert len(token) >= 32
    assert all(c.isalnum() or c in "-_" for c in token)


def test_generate_session_token_is_unique_per_call():
    assert generate_session_token() != generate_session_token()


def test_hash_session_token_is_deterministic():
    token = "fixed-example-token"  # noqa: S105 (test fixture, not a real credential)
    assert hash_session_token(token) == hash_session_token(token)


def test_hash_session_token_differs_for_different_tokens():
    assert hash_session_token("token-a") != hash_session_token("token-b")


def test_hash_session_token_is_a_sha256_hex_digest():
    digest = hash_session_token("token")
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)
