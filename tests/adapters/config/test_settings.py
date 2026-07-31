"""Tests for environment-driven application settings."""

import pytest
from pydantic import ValidationError

from vibeguard.adapters.config.settings import Settings


def test_settings_uses_defaults_when_only_database_url_given():
    settings = Settings(database_url="postgresql+psycopg://localhost/db")
    assert settings.max_file_count == 20_000
    assert settings.clone_timeout_seconds == 60


def test_settings_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", "postgresql+psycopg://localhost/db")
    monkeypatch.setenv("VIBEGUARD_MAX_FILE_COUNT", "5")
    settings = Settings()
    assert settings.max_file_count == 5


def test_settings_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VIBEGUARD_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings()
