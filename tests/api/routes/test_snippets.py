"""Tests for POST /snippets through the full request/response cycle."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import get_db_session, get_settings
from vibeguard.api.routes.snippets import router


def _build_test_app(db_session: Session, settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def test_submit_snippet_happy_path_returns_201(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post("/snippets", json={"content": "print(1)", "filename": "app.py"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scan_pending"
    assert body["filename"] == "app.py"
    assert body["rejection_reason"] is None


def test_submit_snippet_without_filename_uses_a_default(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post("/snippets", json={"content": "print(1)"})

    assert response.status_code == 201
    assert response.json()["filename"]


def test_submit_snippet_empty_content_returns_201_rejected(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post("/snippets", json={"content": "   "})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "empty_content"


def test_submit_snippet_oversized_content_returns_201_rejected(
    db_session: Session, settings_factory
):
    settings = settings_factory(max_file_size_bytes=10)
    client = TestClient(_build_test_app(db_session, settings))

    response = client.post("/snippets", json={"content": "x" * 50})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "too_large"


def test_submit_snippet_missing_body_field_returns_422(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post("/snippets", json={})

    assert response.status_code == 422
