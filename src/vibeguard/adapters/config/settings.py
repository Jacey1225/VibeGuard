"""Application configuration loaded from environment variables."""

import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from vibeguard.core.limits import (
    DEFAULT_CLONE_TIMEOUT_SECONDS,
    DEFAULT_GITHUB_API_TIMEOUT_SECONDS,
    DEFAULT_INGEST_THREAD_POOL_SIZE,
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_MAX_CONCURRENT_LLM_CALLS,
    DEFAULT_MAX_CONCURRENT_REMEDIATION_LLM_CALLS,
    DEFAULT_MAX_FILE_COUNT,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_LLM_CALLS_PER_REMEDIATION,
    DEFAULT_MAX_LLM_CALLS_PER_SCAN,
    DEFAULT_MAX_TOTAL_SIZE_BYTES,
    DEFAULT_OAUTH_STATE_COOKIE_TTL_SECONDS,
    DEFAULT_PRECHECK_SIZE_FUDGE_FACTOR,
    DEFAULT_REMEDIATION_LLM_MAX_TOKENS,
    DEFAULT_SESSION_TTL_HOURS,
)


class Settings(BaseSettings):
    """Runtime configuration, overridable via `VIBEGUARD_*` environment variables."""

    # populate_by_name=True: `openrouter_api_key` also needs to be
    # constructible by its Python attribute name (tests, direct
    # construction), not only via its `OPENROUTER_API_KEY` env alias.
    model_config = SettingsConfigDict(env_prefix="VIBEGUARD_", populate_by_name=True)

    database_url: str
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    max_total_size_bytes: int = DEFAULT_MAX_TOTAL_SIZE_BYTES
    max_file_count: int = DEFAULT_MAX_FILE_COUNT
    clone_timeout_seconds: int = DEFAULT_CLONE_TIMEOUT_SECONDS
    github_api_timeout_seconds: float = DEFAULT_GITHUB_API_TIMEOUT_SECONDS
    precheck_size_fudge_factor: float = DEFAULT_PRECHECK_SIZE_FUDGE_FACTOR
    ingest_thread_pool_size: int = DEFAULT_INGEST_THREAD_POOL_SIZE

    # Vulnerability scan engine (OpenRouter -> DeepSeek).
    # `OPENROUTER_API_KEY` deliberately breaks the `VIBEGUARD_` prefix
    # convention above, to match the variable name already in this
    # project's .env rather than asking for a rename.
    openrouter_api_key: SecretStr = Field(validation_alias="OPENROUTER_API_KEY")
    openrouter_model: str = "deepseek/deepseek-chat-v3.1"
    llm_request_timeout_seconds: float = DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS
    llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS
    max_llm_calls_per_scan: int = DEFAULT_MAX_LLM_CALLS_PER_SCAN
    max_concurrent_llm_calls: int = DEFAULT_MAX_CONCURRENT_LLM_CALLS

    # Remediation engine: same OpenRouter/DeepSeek backend, a full-file
    # rewrite prompt instead of a findings-confirmation prompt.
    remediation_llm_max_tokens: int = DEFAULT_REMEDIATION_LLM_MAX_TOKENS
    max_llm_calls_per_remediation: int = DEFAULT_MAX_LLM_CALLS_PER_REMEDIATION
    max_concurrent_remediation_llm_calls: int = DEFAULT_MAX_CONCURRENT_REMEDIATION_LLM_CALLS

    # GitHub OAuth (user login + the write-scoped token used to push
    # approved remediations). No existing-.env name to match, so these
    # follow the normal VIBEGUARD_ prefix convention -- no Field()
    # override needed, unlike openrouter_api_key above.
    github_oauth_client_id: str
    github_oauth_client_secret: SecretStr
    github_oauth_redirect_uri: str
    frontend_redirect_base_url: str

    # A `Fernet.generate_key()` value, provisioned once out-of-band --
    # encrypts every stored GitHub OAuth access token at rest.
    token_encryption_key: SecretStr

    session_ttl_hours: int = DEFAULT_SESSION_TTL_HOURS
    oauth_state_cookie_ttl_seconds: int = DEFAULT_OAUTH_STATE_COOKIE_TTL_SECONDS


_DEFAULT_CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]


def load_cors_allowed_origins() -> list[str]:
    """Read allowed CORS origins from `VIBEGUARD_CORS_ALLOWED_ORIGINS`.

    Comma-separated (e.g. "http://localhost:5173,https://app.example.com"),
    defaulting to the frontend's own Vite dev server origin. Never treat a
    wildcard as acceptable here -- see code-security's CORS guidance.

    Reads the environment directly rather than going through `Settings`,
    because `create_app()` must register CORS middleware before the app
    starts serving, while `Settings()` -- which requires unrelated fields
    like `database_url` -- is deliberately constructed later, in
    `lifespan()`, so importing the app module doesn't require every env
    var to be set.
    """
    raw = os.environ.get("VIBEGUARD_CORS_ALLOWED_ORIGINS")
    if not raw:
        return list(_DEFAULT_CORS_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
