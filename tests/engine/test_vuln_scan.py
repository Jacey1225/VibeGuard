"""Tests for the vulnerability scan orchestration."""

import threading
import time
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

import vibeguard.engine.llm_confirmation as llm_confirmation_module
import vibeguard.engine.vuln_scan as vuln_scan_module
from vibeguard.adapters.db.finding_store import list_findings_for_repository
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.adapters.llm.openrouter_client import LlmApiUnavailableError
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.repository_status import RepositoryStatus, ScanFailureReason
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.vuln_scan import run_scan


def _make_repository(session: Session) -> RepositoryModel:
    repository = RepositoryModel(
        source_url="u",
        owner="o",
        name="r",
        status=RepositoryStatus.SCAN_PENDING_IMPLEMENTATION,
    )
    session.add(repository)
    session.flush()
    return repository


def _add_file(
    session: Session, repository: RepositoryModel, relative_path: str, content: str
) -> None:
    session.add(
        RepositoryFileModel(
            repository_id=repository.id,
            relative_path=relative_path,
            size_bytes=len(content),
            content=content,
        )
    )


def _fake_finding(relative_path: str, category: VulnCategory = VulnCategory.INJECTION) -> Finding:
    return Finding(
        category=category,
        severity=Severity.HIGH,
        title="t",
        description="d",
        remediation="r",
        relative_path=relative_path,
        line_number=1,
        source=FindingSource.HEURISTIC_CONFIRMED,
        model="test-model",
    )


def test_run_scan_clean_files_never_call_the_llm(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "clean.py", "def f(x):\n    return x + 1")
    db_session.flush()

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    call_spy.assert_not_called()


def test_run_scan_multi_category_file_triggers_exactly_one_call(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(
        db_session,
        repository,
        "multi.py",
        'cursor.execute(f"SELECT * FROM t WHERE id = {x}")\nAPI_KEY = "sk_live_abcdef1234567890"',
    )
    db_session.flush()

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert call_spy.call_count == 1


def test_run_scan_persists_confirmed_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "flagged.py", 'password = "admin"')
    db_session.flush()

    monkeypatch.setattr(
        llm_confirmation_module,
        "confirm_findings",
        Mock(return_value=[_fake_finding("flagged.py")]),
    )

    updated = run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert updated.status == RepositoryStatus.SCANNED
    findings = list_findings_for_repository(db_session, repository.id)
    assert len(findings) == 1
    assert findings[0].relative_path == "flagged.py"


def test_run_scan_marks_scanning_before_finalizing(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    db_session.flush()

    observed_statuses = []
    real_update_status = vuln_scan_module.update_repository_status

    def _tracking_update_status(session, repo, status, rejection_reason=None):
        observed_statuses.append(status)
        return real_update_status(session, repo, status, rejection_reason)

    monkeypatch.setattr(vuln_scan_module, "update_repository_status", _tracking_update_status)

    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert observed_statuses[0] == RepositoryStatus.SCANNING


def test_run_scan_one_failing_call_does_not_abort_the_rest(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "a.py", 'password = "admin"')
    _add_file(db_session, repository, "b.py", 'password = "changeme"')
    db_session.flush()

    def fake_confirm_findings(result, content, client, api_key, model, timeout_seconds, max_tokens):
        if result.relative_path == "a.py":
            raise LlmApiUnavailableError("simulated")
        return [_fake_finding("b.py")]

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", fake_confirm_findings)

    updated = run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert updated.status == RepositoryStatus.SCANNED
    assert updated.scan_incomplete is True
    assert "1 of 2" in (updated.scan_incomplete_reason or "")
    findings = list_findings_for_repository(db_session, repository.id)
    assert len(findings) == 1
    assert findings[0].relative_path == "b.py"


def test_run_scan_total_llm_failure_sets_scan_failed(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "a.py", 'password = "admin"')
    db_session.flush()

    def always_fails(result, content, client, api_key, model, timeout_seconds, max_tokens):
        raise LlmApiUnavailableError("simulated")

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", always_fails)

    updated = run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert updated.status == RepositoryStatus.SCAN_FAILED
    assert updated.scan_failure_reason == ScanFailureReason.LLM_UNAVAILABLE
    assert list_findings_for_repository(db_session, repository.id) == []


def test_run_scan_caps_llm_calls_and_marks_incomplete(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    for i in range(5):
        _add_file(db_session, repository, f"flagged{i}.py", 'password = "admin"')
    db_session.flush()

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    settings = settings_factory(max_llm_calls_per_scan=2)
    updated = run_scan(repository, db_session, llm_client=object(), settings=settings)

    assert call_spy.call_count == 2
    assert updated.scan_incomplete is True
    assert "max_llm_calls_per_scan" in (updated.scan_incomplete_reason or "")


def test_run_scan_rescan_replaces_prior_findings(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "a.py", 'password = "admin"')
    db_session.flush()

    monkeypatch.setattr(
        llm_confirmation_module, "confirm_findings", Mock(return_value=[_fake_finding("a.py")])
    )
    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())
    assert len(list_findings_for_repository(db_session, repository.id)) == 1

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", Mock(return_value=[]))
    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    assert list_findings_for_repository(db_session, repository.id) == []


def test_run_scan_includes_dependency_manifest_finding(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "requirements.txt", "fastapi==0.115.6\n")
    db_session.flush()

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", Mock(return_value=[]))

    run_scan(repository, db_session, llm_client=object(), settings=settings_factory())

    findings = list_findings_for_repository(db_session, repository.id)
    assert len(findings) == 1
    assert findings[0].category == VulnCategory.VULNERABLE_DEPENDENCIES
    assert findings[0].source == FindingSource.HEURISTIC_ONLY


def test_run_scan_with_selected_categories_skips_files_matching_only_other_categories(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "secret.py", 'API_KEY = "sk_live_abcdef1234567890"')
    db_session.flush()

    call_spy = Mock(return_value=[])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_scan(
        repository,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.INJECTION}),
    )

    call_spy.assert_not_called()


def test_run_scan_with_selected_categories_still_confirms_matching_files(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(
        db_session,
        repository,
        "multi.py",
        'cursor.execute(f"SELECT * FROM t WHERE id = {x}")\nAPI_KEY = "sk_live_abcdef1234567890"',
    )
    db_session.flush()

    call_spy = Mock(return_value=[_fake_finding("multi.py")])
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    run_scan(
        repository,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.INJECTION}),
    )

    assert call_spy.call_count == 1
    confirmed_categories = call_spy.call_args.args[0].categories
    assert confirmed_categories == (VulnCategory.INJECTION,)


def test_run_scan_excludes_dependency_manifest_finding_when_category_not_selected(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "requirements.txt", "fastapi==0.115.6\n")
    db_session.flush()

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", Mock(return_value=[]))

    run_scan(
        repository,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.INJECTION}),
    )

    assert list_findings_for_repository(db_session, repository.id) == []


def test_run_scan_includes_dependency_manifest_finding_when_category_selected(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    _add_file(db_session, repository, "requirements.txt", "fastapi==0.115.6\n")
    db_session.flush()

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", Mock(return_value=[]))

    run_scan(
        repository,
        db_session,
        llm_client=object(),
        settings=settings_factory(),
        selected_categories=frozenset({VulnCategory.VULNERABLE_DEPENDENCIES}),
    )

    findings = list_findings_for_repository(db_session, repository.id)
    assert len(findings) == 1
    assert findings[0].category == VulnCategory.VULNERABLE_DEPENDENCIES


def test_run_scan_respects_max_concurrent_llm_calls(
    db_session: Session, settings_factory, monkeypatch: pytest.MonkeyPatch
):
    repository = _make_repository(db_session)
    for i in range(9):
        _add_file(db_session, repository, f"flagged{i}.py", 'password = "admin"')
    db_session.flush()

    lock = threading.Lock()
    active = 0
    max_seen = 0

    def fake_confirm_findings(result, content, client, api_key, model, timeout_seconds, max_tokens):
        nonlocal active, max_seen
        with lock:
            active += 1
            max_seen = max(max_seen, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return []

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", fake_confirm_findings)

    settings = settings_factory(max_concurrent_llm_calls=3)
    run_scan(repository, db_session, llm_client=object(), settings=settings)

    assert max_seen <= 3
    assert max_seen > 1
