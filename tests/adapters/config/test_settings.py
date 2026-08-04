"""Tests for environment-driven application settings."""

import pytest
from pydantic import ValidationError

from tests.conftest import REQUIRED_SETTINGS_KWARGS
from vibeguard.adapters.config.settings import Settings, load_cors_allowed_origins

_REQUIRED_ENV = {
    "VIBEGUARD_DATABASE_URL": REQUIRED_SETTINGS_KWARGS["database_url"],
    "OPENROUTER_API_KEY": REQUIRED_SETTINGS_KWARGS["openrouter_api_key"],
    "VIBEGUARD_GITHUB_OAUTH_CLIENT_ID": REQUIRED_SETTINGS_KWARGS["github_oauth_client_id"],
    "VIBEGUARD_GITHUB_OAUTH_CLIENT_SECRET": REQUIRED_SETTINGS_KWARGS["github_oauth_client_secret"],
    "VIBEGUARD_GITHUB_OAUTH_REDIRECT_URI": REQUIRED_SETTINGS_KWARGS["github_oauth_redirect_uri"],
    "VIBEGUARD_FRONTEND_REDIRECT_BASE_URL": REQUIRED_SETTINGS_KWARGS["frontend_redirect_base_url"],
    "VIBEGUARD_TOKEN_ENCRYPTION_KEY": REQUIRED_SETTINGS_KWARGS["token_encryption_key"],
}


def _set_required_env(monkeypatch: pytest.MonkeyPatch, *, exclude: str = "") -> None:
    for key, value in _REQUIRED_ENV.items():
        if key != exclude:
            monkeypatch.setenv(key, str(value))


def test_settings_uses_defaults_when_only_required_fields_given():
    settings = Settings(**REQUIRED_SETTINGS_KWARGS)
    assert settings.max_file_count == 20_000
    assert settings.clone_timeout_seconds == 60
    assert settings.max_llm_calls_per_scan == 150
    assert settings.session_ttl_hours == 24


def test_settings_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("VIBEGUARD_MAX_FILE_COUNT", "5")
    settings = Settings()
    assert settings.max_file_count == 5


@pytest.mark.parametrize("missing_env_var", list(_REQUIRED_ENV))
def test_settings_missing_required_field_raises(
    monkeypatch: pytest.MonkeyPatch, missing_env_var: str
):
    _set_required_env(monkeypatch, exclude=missing_env_var)
    monkeypatch.delenv(missing_env_var, raising=False)
    with pytest.raises(ValidationError):
        Settings()


def test_settings_openrouter_api_key_uses_unprefixed_env_var_name(
    monkeypatch: pytest.MonkeyPatch,
):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-value")
    settings = Settings()
    assert settings.openrouter_api_key.get_secret_value() == "sk-or-test-value"


def test_settings_secret_fields_repr_is_masked():
    settings = Settings(**REQUIRED_SETTINGS_KWARGS)
    rendered = repr(settings)
    assert "test-openrouter-key" not in rendered
    assert "test-oauth-client-secret" not in rendered
    assert REQUIRED_SETTINGS_KWARGS["token_encryption_key"] not in rendered


def test_load_cors_allowed_origins_defaults_to_local_frontend_dev_origin(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("VIBEGUARD_CORS_ALLOWED_ORIGINS", raising=False)
    assert load_cors_allowed_origins() == ["http://localhost:5173"]


def test_load_cors_allowed_origins_parses_comma_separated_env_var(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        "VIBEGUARD_CORS_ALLOWED_ORIGINS", "http://localhost:5173, https://app.example.com"
    )
    assert load_cors_allowed_origins() == ["http://localhost:5173", "https://app.example.com"]
