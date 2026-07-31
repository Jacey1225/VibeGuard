"""Tests for the FastAPI app factory and lifespan wiring."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from vibeguard.api.main import create_app


def test_create_app_lifespan_wires_up_shared_resources(
    monkeypatch: pytest.MonkeyPatch, db_engine: Engine
):
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", str(db_engine.url))
    app = create_app()

    with TestClient(app) as client:
        assert app.state.session_factory is not None
        assert app.state.github_client is not None
        assert app.state.settings.database_url == str(db_engine.url)

        response = client.get("/docs")
        assert response.status_code == 200
