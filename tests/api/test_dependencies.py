"""Tests for FastAPI Depends() wrappers exposing shared adapters."""

from types import SimpleNamespace

import httpx
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from tests.conftest import REQUIRED_SETTINGS_KWARGS
from vibeguard.adapters.config.settings import Settings
from vibeguard.api.dependencies import (
    get_db_session,
    get_github_client,
    get_llm_client,
    get_settings,
)


def _fake_request(**state: object) -> SimpleNamespace:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


def test_get_github_client_returns_the_shared_client():
    client = httpx.Client()
    try:
        request = _fake_request(github_client=client)
        assert get_github_client(request) is client
    finally:
        client.close()


def test_get_llm_client_returns_the_shared_client():
    client = httpx.Client()
    try:
        request = _fake_request(llm_client=client)
        assert get_llm_client(request) is client
    finally:
        client.close()


def test_get_settings_returns_the_shared_settings():
    settings = Settings(**REQUIRED_SETTINGS_KWARGS)
    request = _fake_request(settings=settings)
    assert get_settings(request) is settings


def test_get_db_session_yields_a_working_session_from_the_shared_factory(db_engine):
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    request = _fake_request(session_factory=session_factory)

    generator = get_db_session(request)
    session = next(generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
