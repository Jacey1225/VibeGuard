"""Confirming heuristic-flagged content via the LLM within a per-scan call budget.

Shared by every scan pipeline that confirms heuristic hits via the LLM
(repository scans, plain-text snippet scans): deciding which flagged
files fit the call budget, running the bounded-concurrency confirmation
calls, and turning the raw outcome into a source-agnostic completion
verdict are identical regardless of what the scanned content came from
-- this module operates purely on `HeuristicScanResult` and a
`relative_path -> content` mapping, never on a repository or snippet
type directly.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import httpx

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.llm.openrouter_client import (
    LlmApiUnavailableError,
    LlmResponseParseError,
    confirm_findings,
)
from vibeguard.core.finding import Finding
from vibeguard.core.heuristics.run_heuristics import HeuristicScanResult

logger = logging.getLogger(__name__)


@dataclass
class ScanOutcome:
    """Raw counts from the LLM-confirmation phase, before a status is derived from them."""

    findings: list[Finding] = field(default_factory=list)
    attempted_calls: int = 0
    successful_calls: int = 0
    files_over_cap: int = 0


@dataclass(frozen=True)
class ScanCompletion:
    """Whether a scan fully succeeded, partially completed, or failed outright.

    Deliberately independent of any particular status enum: each
    pipeline (repository, snippet) maps `total_failure`/`incomplete`
    onto its own status type rather than sharing one.
    """

    total_failure: bool
    incomplete: bool
    incomplete_reason: str | None


def cap_to_call_budget(
    heuristic_results: list[HeuristicScanResult], max_calls: int
) -> tuple[list[HeuristicScanResult], int]:
    """Admit at most `max_calls` results, decided upfront.

    Deciding the full admitted set before any concurrent work starts
    means the cap needs no lock to stay race-free.
    """
    if len(heuristic_results) <= max_calls:
        return heuristic_results, 0
    return heuristic_results[:max_calls], len(heuristic_results) - max_calls


def confirm_flagged_files(
    admitted: list[HeuristicScanResult],
    content_by_path: dict[str, str],
    llm_client: httpx.Client,
    settings: Settings,
) -> ScanOutcome:
    """Confirm every admitted heuristic result via the LLM, with bounded concurrency."""
    outcome = ScanOutcome(attempted_calls=len(admitted))
    if not admitted:
        return outcome

    with ThreadPoolExecutor(max_workers=settings.max_concurrent_llm_calls) as executor:
        call_results = list(
            executor.map(
                lambda result: _confirm_one_file(result, content_by_path, llm_client, settings),
                admitted,
            )
        )

    for call_result in call_results:
        if call_result is None:
            continue
        outcome.successful_calls += 1
        outcome.findings.extend(call_result)
    return outcome


def _confirm_one_file(
    result: HeuristicScanResult,
    content_by_path: dict[str, str],
    llm_client: httpx.Client,
    settings: Settings,
) -> list[Finding] | None:
    """Confirm one file's flagged categories. Returns `None` on failure (logged, not raised)."""
    try:
        return confirm_findings(
            result,
            content_by_path[result.relative_path],
            llm_client,
            settings.openrouter_api_key,
            settings.openrouter_model,
            settings.llm_request_timeout_seconds,
            settings.llm_max_tokens,
        )
    except (LlmApiUnavailableError, LlmResponseParseError) as error:
        # Error type only -- never the exception's full message, which
        # can echo back response content (code-security: no full
        # payloads in logs, even on failure).
        logger.warning(
            "LLM confirmation failed for %s (categories=%s): %s",
            result.relative_path,
            [category.value for category in result.categories],
            type(error).__name__,
        )
        return None


def derive_scan_completion(outcome: ScanOutcome) -> ScanCompletion:
    """Turn a raw `ScanOutcome` into a source-agnostic completion verdict.

    A total failure (every attempted call failed) is distinguished from
    a merely incomplete scan (some calls failed, or the budget cap was
    hit) so a total outage never looks like "we scanned it and it's
    clean."
    """
    failed_calls = outcome.attempted_calls - outcome.successful_calls
    total_failure = outcome.attempted_calls > 0 and outcome.successful_calls == 0
    if total_failure:
        return ScanCompletion(total_failure=True, incomplete=False, incomplete_reason=None)

    incomplete_reasons = []
    if outcome.files_over_cap > 0:
        incomplete_reasons.append(
            f"{outcome.files_over_cap} flagged file(s) exceeded max_llm_calls_per_scan"
        )
    if failed_calls > 0:
        incomplete_reasons.append(f"{failed_calls} of {outcome.attempted_calls} LLM call(s) failed")

    return ScanCompletion(
        total_failure=False,
        incomplete=bool(incomplete_reasons),
        incomplete_reason="; ".join(incomplete_reasons) or None,
    )
