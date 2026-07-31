"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from vibeguard.core.limits import (
    DEFAULT_CLONE_TIMEOUT_SECONDS,
    DEFAULT_GITHUB_API_TIMEOUT_SECONDS,
    DEFAULT_MAX_FILE_COUNT,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_TOTAL_SIZE_BYTES,
    DEFAULT_PRECHECK_SIZE_FUDGE_FACTOR,
)


class Settings(BaseSettings):
    """Runtime configuration, overridable via `VIBEGUARD_*` environment variables."""

    model_config = SettingsConfigDict(env_prefix="VIBEGUARD_")

    database_url: str
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES
    max_total_size_bytes: int = DEFAULT_MAX_TOTAL_SIZE_BYTES
    max_file_count: int = DEFAULT_MAX_FILE_COUNT
    clone_timeout_seconds: int = DEFAULT_CLONE_TIMEOUT_SECONDS
    github_api_timeout_seconds: float = DEFAULT_GITHUB_API_TIMEOUT_SECONDS
    precheck_size_fudge_factor: float = DEFAULT_PRECHECK_SIZE_FUDGE_FACTOR
