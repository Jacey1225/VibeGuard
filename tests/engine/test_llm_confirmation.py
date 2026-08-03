"""Tests for the shared LLM-confirmation logic used by every scan pipeline."""

from unittest.mock import Mock

import pytest

import vibeguard.engine.llm_confirmation as llm_confirmation_module
from vibeguard.adapters.llm.openrouter_client import LlmApiUnavailableError
from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.heuristics.run_heuristics import HeuristicScanResult
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.llm_confirmation import (
    ScanOutcome,
    cap_to_call_budget,
    confirm_flagged_files,
    derive_scan_completion,
)


def _result(relative_path: str = "a.py") -> HeuristicScanResult:
    return HeuristicScanResult(
        relative_path=relative_path, categories=(VulnCategory.INJECTION,), hits=()
    )


def _finding(relative_path: str = "a.py") -> Finding:
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


def test_cap_to_call_budget_admits_everything_under_the_cap():
    results = [_result("a.py"), _result("b.py")]

    admitted, over_cap = cap_to_call_budget(results, max_calls=5)

    assert admitted == results
    assert over_cap == 0


def test_cap_to_call_budget_truncates_and_counts_the_overflow():
    results = [_result(f"f{i}.py") for i in range(5)]

    admitted, over_cap = cap_to_call_budget(results, max_calls=2)

    assert admitted == results[:2]
    assert over_cap == 3


def test_confirm_flagged_files_with_no_admitted_results_never_calls_the_llm(
    settings_factory, monkeypatch: pytest.MonkeyPatch
):
    call_spy = Mock()
    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", call_spy)

    outcome = confirm_flagged_files([], {}, llm_client=object(), settings=settings_factory())

    call_spy.assert_not_called()
    assert outcome.attempted_calls == 0
    assert outcome.successful_calls == 0


def test_confirm_flagged_files_collects_findings_from_every_successful_call(
    settings_factory, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        llm_confirmation_module, "confirm_findings", Mock(return_value=[_finding("a.py")])
    )

    outcome = confirm_flagged_files(
        [_result("a.py")], {"a.py": "content"}, llm_client=object(), settings=settings_factory()
    )

    assert outcome.attempted_calls == 1
    assert outcome.successful_calls == 1
    assert outcome.findings == [_finding("a.py")]


def test_confirm_flagged_files_logs_and_continues_past_a_failing_call(
    settings_factory, monkeypatch: pytest.MonkeyPatch
):
    def always_fails(result, content, client, api_key, model, timeout_seconds, max_tokens):
        raise LlmApiUnavailableError("simulated")

    monkeypatch.setattr(llm_confirmation_module, "confirm_findings", always_fails)

    outcome = confirm_flagged_files(
        [_result("a.py")], {"a.py": "content"}, llm_client=object(), settings=settings_factory()
    )

    assert outcome.attempted_calls == 1
    assert outcome.successful_calls == 0
    assert outcome.findings == []


def test_derive_scan_completion_no_calls_attempted_is_not_a_failure():
    completion = derive_scan_completion(ScanOutcome())

    assert completion.total_failure is False
    assert completion.incomplete is False


def test_derive_scan_completion_all_calls_succeed_is_complete():
    outcome = ScanOutcome(attempted_calls=3, successful_calls=3)

    completion = derive_scan_completion(outcome)

    assert completion.total_failure is False
    assert completion.incomplete is False
    assert completion.incomplete_reason is None


def test_derive_scan_completion_every_call_failing_is_total_failure():
    outcome = ScanOutcome(attempted_calls=2, successful_calls=0)

    completion = derive_scan_completion(outcome)

    assert completion.total_failure is True
    assert completion.incomplete is False
    assert completion.incomplete_reason is None


def test_derive_scan_completion_partial_failure_is_incomplete_not_total_failure():
    outcome = ScanOutcome(attempted_calls=2, successful_calls=1)

    completion = derive_scan_completion(outcome)

    assert completion.total_failure is False
    assert completion.incomplete is True
    assert "1 of 2" in (completion.incomplete_reason or "")


def test_derive_scan_completion_files_over_cap_marks_incomplete():
    outcome = ScanOutcome(attempted_calls=1, successful_calls=1, files_over_cap=4)

    completion = derive_scan_completion(outcome)

    assert completion.total_failure is False
    assert completion.incomplete is True
    assert "4 flagged file(s)" in (completion.incomplete_reason or "")
