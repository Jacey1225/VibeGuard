"""Tests for the plain-text snippet vulnerability scan orchestration."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

import vibeguard.engine.llm_confirmation as llm_confirmation_module
import vibeguard.engine.snippet_scan as snippet_scan_module
from vibeguard.adapters.db.snippet_finding_store import list_findings_for_snippet
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.adapters.llm.openrouter_client import LlmApiUnavailableError
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.snippet_scan import run_snippet_scan


def _make_snippet(session: Session, content: str, filename: str = "a.py") -> SnippetModel:
    snippet = SnippetModel(
        content=content,
        filename=filename,
        size_bytes=len(content),
        status=SnippetStatus.SCAN_PENDING,
    )
    session.add(snippet)
    session.flush()
    return snippet


def _fake_finding(relative_path: str = "a.py") -> Finding:
    return Finding(
        category=VulnCategory.INJECTION,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path=relative_path,
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )


def test_run_snippet_scan_clean_content_never_calls_the_llm(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, "def f(x):\n    return x + 1")

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings_factory())

    call_spy.assert_not_called()


def test_run_snippet_scan_flagged_content_triggers_exactly_one_call(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"')

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings_factory())

    assert call_spy.call_count == 1


def test_run_snippet_scan_persists_confirmed_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"', filename="flagged.py")

    monkeypatch.setattr(
        llm_confirmation_module,
        "confirm_findings",
        Mock(return_value=[_fake_finding("flagged.py")]),
    )

    updated = run_snippet_scan(
        snippet, db_session, llm_client=object(), settings=settings_factory()
    )

    assert updated.status == SnippetStatus.SCANNED
    findings = list_findings_for_snippet(db_session, snippet.id)
    assert len(findings) == 1
    assert findings[0].relative_path == "flagged.py"


def test_run_snippet_scan_marks_scanning_before_finalizing(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, "print(1)")

    observed_statuses = []
    real_update_status = snippet_scan_module.update_snippet_status

    def _tracking_update_status(session, snippet, status):
        observed_statuses.append(status)
        return real_update_status(session, snippet, status)

    monkeypatch.setattr(snippet_scan_module, "update_snippet_status", _tracking_update_status)

    run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings_factory())

    assert observed_statuses[0] == SnippetStatus.SCANNING


def test_run_snippet_scan_total_llm_failure_sets_scan_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"')

    def always_fails(result, content, client, api_key, model, timeout_seconds, max_tokens):
        raise LlmApiUnavailableError("simulated")

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", always_fails)

    updated = run_snippet_scan(
        snippet, db_session, llm_client=object(), settings=settings_factory()
    )

    assert updated.status == SnippetStatus.SCAN_FAILED
    assert list_findings_for_snippet(db_session, snippet.id) == []


def test_run_snippet_scan_caps_llm_calls_and_marks_incomplete(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"')

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    settings = settings_factory(max_llm_calls_per_scan=0)
    updated = run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings)

    call_spy.assert_not_called()
    assert updated.scan_incomplete is True
    assert "max_llm_calls_per_scan" in (updated.scan_incomplete_reason or "")


def test_run_snippet_scan_rescan_replaces_prior_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"')

    monkeypatch.setattr(
        llm_confirmation_module, "confirm_findings", Mock(return_value=[_fake_finding("a.py")])
    )
    run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings_factory())
    assert len(list_findings_for_snippet(db_session, snippet.id)) == 1

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", Mock(return_value=[]))
    run_snippet_scan(snippet, db_session, llm_client=object(), settings=settings_factory())

    assert list_findings_for_snippet(db_session, snippet.id) == []


def test_run_snippet_scan_with_selected_categories_skips_non_matching_content(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'API_KEY = "sk_live_abcdef1234567890"')

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_snippet_scan(
        snippet,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.INJECTION}),
    )

    call_spy.assert_not_called()


def test_run_snippet_scan_with_selected_categories_still_confirms_matching_content(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    snippet = _make_snippet(db_session, 'password = "admin"')

    call_spy = Mock(return_value=[_fake_finding()])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    updated = run_snippet_scan(
        snippet,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.SECURITY_MISCONFIGURATION}),
    )

    assert call_spy.call_count == 1
    assert updated.status == SnippetStatus.SCANNED
    assert len(list_findings_for_snippet(db_session, snippet.id)) == 1
