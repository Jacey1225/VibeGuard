"""Tests for POST /snippets/{id}/scan and GET /snippets/{id}/findings."""

from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import vibeguard.engine.llm_confirmation as llm_confirmation_module
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.api.dependencies import get_db_session, get_llm_client, get_settings
from vibeguard.api.error_handlers import handle_snippet_not_found, handle_snippet_not_ready_for_scan
from vibeguard.api.routes.snippet_scans import router
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetRejectionReason, SnippetStatus
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.snippet_scan import SnippetNotFoundError, SnippetNotReadyForScanError


def _build_test_app(db_session: Session, llm_client: httpx.Client, settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(SnippetNotFoundError, handle_snippet_not_found)
    app.add_exception_handler(SnippetNotReadyForScanError, handle_snippet_not_ready_for_scan)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def _make_snippet(
    session: Session,
    status: SnippetStatus,
    content: str = 'password = "admin"',
    rejection_reason: SnippetRejectionReason | None = None,
) -> SnippetModel:
    snippet = SnippetModel(
        content=content,
        filename="a.py",
        size_bytes=len(content),
        status=status,
        rejection_reason=rejection_reason,
    )
    session.add(snippet)
    session.flush()
    return snippet


def test_scan_snippet_unknown_id_returns_404(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post("/snippets/999999/scan")

    assert response.status_code == 404


def test_scan_snippet_rejected_status_returns_409(db_session: Session, settings_factory):
    snippet = _make_snippet(
        db_session, SnippetStatus.REJECTED, rejection_reason=SnippetRejectionReason.EMPTY_CONTENT
    )
    db_session.commit()
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post(f"/snippets/{snippet.id}/scan")

    assert response.status_code == 409


def test_scan_snippet_happy_path_returns_200_and_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, SnippetStatus.SCAN_PENDING)
    db_session.commit()

    fake_finding = Finding(
        category=VulnCategory.SECURITY_MISCONFIGURATION,
        severity=Severity.MEDIUM,
        title="t",
        description="d",
        remediation="r",
        relative_path="a.py",
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )
    monkeypatch.setattr(
        llm_confirmation_module, "confirm_findings", Mock(return_value=[fake_finding])
    )

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    response = client.post(f"/snippets/{snippet.id}/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scanned"
    assert body["scan_incomplete"] is False


def test_scan_snippet_with_empty_categories_list_returns_422(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session, SnippetStatus.SCAN_PENDING)
    db_session.commit()
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post(f"/snippets/{snippet.id}/scan", json={"categories": []})

    assert response.status_code == 422


def test_scan_snippet_with_selected_categories_only_activates_those(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    # Default fixture content is `password = "admin"`, a
    # security_misconfiguration hit -- selecting only injection must
    # never call the LLM.
    snippet = _make_snippet(db_session, SnippetStatus.SCAN_PENDING)
    db_session.commit()

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    response = client.post(f"/snippets/{snippet.id}/scan", json={"categories": ["injection"]})

    assert response.status_code == 200
    call_spy.assert_not_called()


def test_list_snippet_findings_unknown_snippet_returns_404(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.get("/snippets/999999/findings")

    assert response.status_code == 404


def test_list_snippet_findings_returns_worst_first(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, SnippetStatus.SCAN_PENDING)
    db_session.commit()

    monkeypatch.setattr(
        llm_confirmation_module,
        "confirm_findings",
        Mock(
            return_value=[
                Finding(
                    category=VulnCategory.SECURITY_MISCONFIGURATION,
                    severity=Severity.LOW,
                    title="t1",
                    description="d",
                    remediation="r",
                    relative_path="a.py",
                    line_number=1,
                    source=FindingSource.HEURISTIC_CONFIRMED,
                    model="test-model",
                ),
                Finding(
                    category=VulnCategory.SECURITY_MISCONFIGURATION,
                    severity=Severity.CRITICAL,
                    title="t2",
                    description="d",
                    remediation="r",
                    relative_path="a.py",
                    line_number=2,
                    source=FindingSource.HEURISTIC_CONFIRMED,
                    model="test-model",
                ),
            ]
        ),
    )

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    scan_response = client.post(f"/snippets/{snippet.id}/scan")
    assert scan_response.status_code == 200

    findings_response = client.get(f"/snippets/{snippet.id}/findings")
    assert findings_response.status_code == 200
    findings = findings_response.json()["findings"]
    assert [f["severity"] for f in findings] == ["critical", "low"]
