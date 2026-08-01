"""Tests for POST /repositories/{id}/scan and GET /repositories/{id}/findings."""

from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import vibeguard.engine.vuln_scan as vuln_scan_module
from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.api.dependencies import get_db_session, get_llm_client, get_settings
from vibeguard.api.error_handlers import (
    handle_repository_not_found,
    handle_repository_not_ready_for_scan,
)
from vibeguard.api.routes.scans import router
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.repository_status import RejectionReason, RepositoryStatus
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.vuln_scan import RepositoryNotFoundError, RepositoryNotReadyForScanError


def _build_test_app(db_session: Session, llm_client: httpx.Client, settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RepositoryNotFoundError, handle_repository_not_found)
    app.add_exception_handler(RepositoryNotReadyForScanError, handle_repository_not_ready_for_scan)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def _make_repository(
    session: Session,
    status: RepositoryStatus,
    rejection_reason: RejectionReason | None = None,
) -> RepositoryModel:
    repository = RepositoryModel(
        source_url="u", owner="o", name="r", status=status, rejection_reason=rejection_reason
    )
    session.add(repository)
    session.flush()
    return repository


def test_scan_repository_unknown_id_returns_404(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post("/repositories/999999/scan")

    assert response.status_code == 404


def test_scan_repository_wrong_status_returns_409(db_session: Session, settings_factory):
    repository = _make_repository(db_session, RepositoryStatus.CLONING)
    db_session.commit()
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post(f"/repositories/{repository.id}/scan")

    assert response.status_code == 409


def test_scan_repository_rejected_status_returns_409(db_session: Session, settings_factory):
    repository = _make_repository(
        db_session, RepositoryStatus.REJECTED, RejectionReason.NOT_PUBLIC_OR_NOT_FOUND
    )
    db_session.commit()
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.post(f"/repositories/{repository.id}/scan")

    assert response.status_code == 409


def test_scan_repository_happy_path_returns_200_and_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session, RepositoryStatus.SCAN_PENDING_IMPLEMENTATION)
    db_session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path="a.py",
            size_bytes=20,
            content='password = "admin"',
        )
    )
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
    monkeypatch.setattr(vuln_scan_module, "confirm_findings", Mock(return_value=[fake_finding]))

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    response = client.post(f"/repositories/{repository.id}/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scanned"
    assert body["scan_incomplete"] is False


def test_list_findings_unknown_repository_returns_404(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))

    response = client.get("/repositories/999999/findings")

    assert response.status_code == 404


def test_list_findings_returns_worst_first(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session, RepositoryStatus.SCAN_PENDING_IMPLEMENTATION)
    db_session.add_all(
        [
            RepositoryFileModel(
                repository_id=repository.id,
                relative_path="a.py",
                size_bytes=20,
                content='password = "admin"',
            ),
            RepositoryFileModel(
                repository_id=repository.id,
                relative_path="b.py",
                size_bytes=20,
                content='password = "changeme"',
            ),
        ]
    )
    db_session.commit()

    def fake_confirm_findings(result, content, client, api_key, model, timeout_seconds, max_tokens):
        severity = Severity.LOW if result.relative_path == "a.py" else Severity.CRITICAL
        return [
            Finding(
                category=VulnCategory.SECURITY_MISCONFIGURATION,
                severity=severity,
                title="t",
                description="d",
                remediation="r",
                relative_path=result.relative_path,
                line_number=1,
                source=FindingSource.HEURISTIC_CONFIRMED,
                model="test-model",
            )
        ]

    monkeypatch.setattr(vuln_scan_module, "confirm_findings", fake_confirm_findings)

    client = TestClient(_build_test_app(db_session, httpx.Client(), settings_factory()))
    scan_response = client.post(f"/repositories/{repository.id}/scan")
    assert scan_response.status_code == 200

    findings_response = client.get(f"/repositories/{repository.id}/findings")
    assert findings_response.status_code == 200
    findings = findings_response.json()["findings"]
    assert [f["severity"] for f in findings] == ["critical", "low"]
    assert findings[0]["relative_path"] == "b.py"
