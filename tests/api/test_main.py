"""Tests for the FastAPI app factory and lifespan wiring."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from tests.adapters.config.test_settings import _REQUIRED_ENV
from vibeguard.api.main import create_app


def test_create_app_lifespan_wires_up_shared_resources(
    monkeypatch: pytest.MonkeyPatch, db_engine: Engine
):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", str(db_engine.url))
    app = create_app()

    with TestClient(app) as client:
        assert app.state.session_factory is not None
        assert app.state.github_client is not None
        assert app.state.llm_client is not None
        assert app.state.settings.database_url == str(db_engine.url)

        response = client.get("/docs")
        assert response.status_code == 200


def test_create_app_allows_configured_cors_origin(
    monkeypatch: pytest.MonkeyPatch, db_engine: Engine
):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", str(db_engine.url))
    monkeypatch.delenv("VIBEGUARD_CORS_ALLOWED_ORIGINS", raising=False)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/docs", headers={"Origin": "http://localhost:5173"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_create_app_rejects_unconfigured_cors_origin(
    monkeypatch: pytest.MonkeyPatch, db_engine: Engine
):
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", str(db_engine.url))
    monkeypatch.delenv("VIBEGUARD_CORS_ALLOWED_ORIGINS", raising=False)
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/docs", headers={"Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in response.headers
