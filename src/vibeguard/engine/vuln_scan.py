"""Top-level orchestration for a repository vulnerability scan.

Sequence: load stored files -> run heuristics (pure, sequential) -> cap
and confirm flagged files via the LLM (bounded concurrency) -> replace
prior findings -> finalize status. Every per-file LLM call is a fresh,
independent request — no shared conversation/context across files in a
scan, which is what keeps injected content in one file from bleeding
into another file's analysis (see `adapters/llm/openrouter_client.py`).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import httpx
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.finding_model import FindingModel
from vibeguard.adapters.db.finding_store import (
    delete_findings_for_repository,
    insert_findings,
    list_findings_for_repository,
    list_stored_files_for_repository,
)
from vibeguard.adapters.db.models import RepositoryFileModel, RepositoryModel
from vibeguard.adapters.db.repository_store import (
    get_repository_by_id,
    update_repository_scan_outcome,
    update_repository_status,
)
from vibeguard.adapters.llm.openrouter_client import (
    LlmApiUnavailableError,
    LlmResponseParseError,
    confirm_findings,
)
from vibeguard.core.dependency_manifest import find_dependency_manifest
from vibeguard.core.finding import Finding
from vibeguard.core.heuristics.run_heuristics import HeuristicScanResult, run_heuristics
from vibeguard.core.repository_status import RepositoryStatus, ScanFailureReason

logger = logging.getLogger(__name__)


class RepositoryNotFoundError(RuntimeError):
    """Raised when a repository id doesn't exist."""


class RepositoryNotReadyForScanError(RuntimeError):
    """Raised when a repository isn't in a status that allows scanning."""


_SCANNABLE_STATUSES = frozenset(
    {
        RepositoryStatus.SCAN_PENDING_IMPLEMENTATION,
        RepositoryStatus.SCANNED,
        RepositoryStatus.SCAN_FAILED,
    }
)


@dataclass
class _ScanOutcome:
    """Raw counts from the LLM-confirmation phase, before a status is derived from them."""

    findings: list[Finding] = field(default_factory=list)
    attempted_calls: int = 0
    successful_calls: int = 0
    files_over_cap: int = 0


def run_scan_for_repository(
    repository_id: int, session: Session, llm_client: httpx.Client, settings: Settings
) -> RepositoryModel:
    """Look up a repository, verify it's scannable, and run its scan.

    Raises:
        RepositoryNotFoundError: no repository with this id exists.
        RepositoryNotReadyForScanError: the repository's current status
            doesn't allow scanning (e.g. still cloning, or rejected).
    """
    repository = get_repository_by_id(session, repository_id)
    if repository is None:
        raise RepositoryNotFoundError(f"no repository with id {repository_id}")
    if repository.status not in _SCANNABLE_STATUSES:
        raise RepositoryNotReadyForScanError(
            f"repository {repository_id} has status {repository.status.value}, not ready to scan"
        )
    return run_scan(repository, session, llm_client, settings)


def get_findings_for_repository(repository_id: int, session: Session) -> list[FindingModel]:
    """Look up a repository's findings, worst-first.

    Raises:
        RepositoryNotFoundError: no repository with this id exists.
    """
    repository = get_repository_by_id(session, repository_id)
    if repository is None:
        raise RepositoryNotFoundError(f"no repository with id {repository_id}")
    return list_findings_for_repository(session, repository_id)


def run_scan(
    repository: RepositoryModel, session: Session, llm_client: httpx.Client, settings: Settings
) -> RepositoryModel:
    """Run the full vulnerability scan for one repository.

    Replaces any prior findings for this repository — rescans overwrite,
    they don't accumulate (no scan-history table in v1).
    """
    update_repository_status(session, repository, RepositoryStatus.SCANNING)

    stored_files = list_stored_files_for_repository(session, repository.id)
    content_by_path = {file.relative_path: file.content or "" for file in stored_files}

    heuristic_results = _run_heuristics_over_files(stored_files)
    manifest_finding = find_dependency_manifest([file.relative_path for file in stored_files])

    admitted, files_over_cap = _cap_to_call_budget(
        heuristic_results, settings.max_llm_calls_per_scan
    )
    outcome = _confirm_flagged_files(admitted, content_by_path, llm_client, settings)
    outcome.files_over_cap = files_over_cap
    if manifest_finding is not None:
        outcome.findings.append(manifest_finding)

    return _finalize_scan(session, repository, outcome)


def _run_heuristics_over_files(
    stored_files: list[RepositoryFileModel],
) -> list[HeuristicScanResult]:
    results = []
    for file in stored_files:
        result = run_heuristics(file.relative_path, file.content or "")
        if result is not None:
            results.append(result)
    return results


def _cap_to_call_budget(
    heuristic_results: list[HeuristicScanResult], max_calls: int
) -> tuple[list[HeuristicScanResult], int]:
    """Admit at most `max_calls` results, decided upfront.

    Same admit-before-parallelize pattern as
    `engine/file_ingestion.py`'s budget admission — deciding the full
    admitted set before any concurrent work starts means the cap needs
    no lock to stay race-free.
    """
    if len(heuristic_results) <= max_calls:
        return heuristic_results, 0
    return heuristic_results[:max_calls], len(heuristic_results) - max_calls


def _confirm_flagged_files(
    admitted: list[HeuristicScanResult],
    content_by_path: dict[str, str],
    llm_client: httpx.Client,
    settings: Settings,
) -> _ScanOutcome:
    outcome = _ScanOutcome(attempted_calls=len(admitted))
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


def _finalize_scan(
    session: Session, repository: RepositoryModel, outcome: _ScanOutcome
) -> RepositoryModel:
    delete_findings_for_repository(session, repository.id)
    insert_findings(session, repository.id, outcome.findings)

    failed_calls = outcome.attempted_calls - outcome.successful_calls
    total_failure = outcome.attempted_calls > 0 and outcome.successful_calls == 0

    if total_failure:
        return update_repository_scan_outcome(
            session,
            repository,
            status=RepositoryStatus.SCAN_FAILED,
            scan_incomplete=False,
            scan_incomplete_reason=None,
            scan_failure_reason=ScanFailureReason.LLM_UNAVAILABLE,
        )

    incomplete_reasons = []
    if outcome.files_over_cap > 0:
        incomplete_reasons.append(
            f"{outcome.files_over_cap} flagged file(s) exceeded max_llm_calls_per_scan"
        )
    if failed_calls > 0:
        incomplete_reasons.append(
            f"{failed_calls} of {outcome.attempted_calls} LLM call(s) failed"
        )

    return update_repository_scan_outcome(
        session,
        repository,
        status=RepositoryStatus.SCANNED,
        scan_incomplete=bool(incomplete_reasons),
        scan_incomplete_reason="; ".join(incomplete_reasons) or None,
        scan_failure_reason=None,
    )
