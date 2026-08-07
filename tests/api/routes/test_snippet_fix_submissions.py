"""Tests for POST/GET /snippets/{id}/findings/{finding_id}/fix through the full request cycle."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import (
    insert_snippet_findings,
    list_findings_for_snippet,
)
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.api.dependencies import get_db_session, get_settings
from vibeguard.api.error_handlers import (
    handle_snippet_finding_not_found,
    handle_snippet_fix_content_invalid,
    handle_snippet_fix_submission_not_found,
    handle_snippet_not_found,
)
from vibeguard.api.routes.snippet_fix_submissions import router
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.snippet_fix_submission import (
    SnippetFindingNotFoundError,
    SnippetFixContentInvalidError,
    SnippetFixSubmissionNotFoundError,
)
from vibeguard.engine.snippet_scan import SnippetNotFoundError


def _build_test_app(db_session: Session, settings: Settings) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(SnippetNotFoundError, handle_snippet_not_found)
    app.add_exception_handler(SnippetFindingNotFoundError, handle_snippet_finding_not_found)
    app.add_exception_handler(
        SnippetFixSubmissionNotFoundError, handle_snippet_fix_submission_not_found
    )
    app.add_exception_handler(SnippetFixContentInvalidError, handle_snippet_fix_content_invalid)
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def _make_snippet(session: Session, content: str = 'password = "admin"') -> SnippetModel:
    snippet = SnippetModel(
        content=content, filename="a.py", size_bytes=len(content), status=SnippetStatus.SCAN_PENDING
    )
    session.add(snippet)
    session.flush()
    session.commit()
    return snippet


def _make_finding(session: Session, snippet: SnippetModel) -> SnippetFindingModel:
    finding = Finding(
        category=VulnCategory.SECURITY_MISCONFIGURATION,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path="a.py",
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )
    insert_snippet_findings(session, snippet.id, [finding])
    session.commit()
    return list_findings_for_snippet(session, snippet.id)[0]


def test_submit_fix_happy_path_returns_200_and_the_submission(
    db_session: Session, settings_factory
):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post(
        f"/snippets/{snippet.id}/findings/{finding.id}/fix",
        json={"fixed_content": 'password = get_secret("admin_password")'},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["snippet_finding_id"] == finding.id
    assert body["fixed_content"] == 'password = get_secret("admin_password")'
    assert "remediation" not in body


def test_submit_fix_unknown_finding_returns_404(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post(
        f"/snippets/{snippet.id}/findings/999999/fix", json={"fixed_content": "fix"}
    )

    assert response.status_code == 404


def test_submit_fix_unknown_snippet_returns_404(db_session: Session, settings_factory):
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post("/snippets/999999/findings/1/fix", json={"fixed_content": "fix"})

    assert response.status_code == 404


def test_submit_fix_empty_content_returns_422(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post(
        f"/snippets/{snippet.id}/findings/{finding.id}/fix", json={"fixed_content": "   "}
    )

    assert response.status_code == 422


def test_submit_fix_over_budget_content_returns_422(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    settings = settings_factory(max_file_size_bytes=10)
    client = TestClient(_build_test_app(db_session, settings))

    response = client.post(
        f"/snippets/{snippet.id}/findings/{finding.id}/fix", json={"fixed_content": "x" * 50}
    )

    assert response.status_code == 422


def test_submit_fix_missing_body_field_returns_422(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.post(f"/snippets/{snippet.id}/findings/{finding.id}/fix", json={})

    assert response.status_code == 422


def test_resubmitting_a_fix_overwrites_rather_than_erroring(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    fix_url = f"/snippets/{snippet.id}/findings/{finding.id}/fix"
    first = client.post(fix_url, json={"fixed_content": "first attempt"})
    second = client.post(fix_url, json={"fixed_content": "second attempt"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    fetched = client.get(f"/snippets/{snippet.id}/findings/{finding.id}/fix")
    assert fetched.json()["fixed_content"] == "second attempt"


def test_read_fix_happy_path_returns_200(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))
    client.post(
        f"/snippets/{snippet.id}/findings/{finding.id}/fix", json={"fixed_content": "the fix"}
    )

    response = client.get(f"/snippets/{snippet.id}/findings/{finding.id}/fix")

    assert response.status_code == 200
    assert response.json()["fixed_content"] == "the fix"


def test_read_fix_unknown_finding_returns_404(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.get(f"/snippets/{snippet.id}/findings/999999/fix")

    assert response.status_code == 404


def test_read_fix_no_fix_submitted_yet_returns_404(db_session: Session, settings_factory):
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    response = client.get(f"/snippets/{snippet.id}/findings/{finding.id}/fix")

    assert response.status_code == 404


def test_submit_and_read_fix_routes_require_no_authorization_header(
    db_session: Session, settings_factory
):
    """Confirms both routes are reachable with zero auth, per the spec's explicit boundary."""
    snippet = _make_snippet(db_session)
    finding = _make_finding(db_session, snippet)
    client = TestClient(_build_test_app(db_session, settings_factory()))

    post_response = client.post(
        f"/snippets/{snippet.id}/findings/{finding.id}/fix", json={"fixed_content": "fix"}
    )
    get_response = client.get(f"/snippets/{snippet.id}/findings/{finding.id}/fix")

    assert post_response.status_code != 401
    assert get_response.status_code != 401


def test_router_declares_no_get_current_user_dependency():
    """Static guard: fails if a future change adds get_current_user to either route,
    which would silently reintroduce a GitHub-auth requirement this feature must not have."""
    for route in router.routes:
        dependant = route.dependant  # type: ignore[attr-defined]
        dependency_names = {dep.call.__name__ for dep in dependant.dependencies}
        assert "get_current_user" not in dependency_names
