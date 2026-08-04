"""Top-level orchestration for a repository vulnerability scan.

Sequence: load stored files -> run heuristics (pure, sequential) -> cap
and confirm flagged files via the LLM (bounded concurrency, see
`engine/llm_confirmation.py`) -> replace prior findings -> finalize
status. Every per-file LLM call is a fresh, independent request — no
shared conversation/context across files in a scan, which is what keeps
injected content in one file from bleeding into another file's analysis
(see `adapters/llm/openrouter_client.py`).
"""

from __future__ import annotations

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
from vibeguard.core.dependency_manifest import find_dependency_manifest
from vibeguard.core.heuristics.category_filter import filter_to_categories
from vibeguard.core.heuristics.run_heuristics import HeuristicScanResult, run_heuristics
from vibeguard.core.repository_status import RepositoryStatus, ScanFailureReason
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.llm_confirmation import (
    ScanOutcome,
    cap_to_call_budget,
    confirm_flagged_files,
    derive_scan_completion,
)


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


def run_scan_for_repository(
    repository_id: int,
    session: Session,
    llm_client: httpx.Client,
    settings: Settings,
    selected_categories: frozenset[VulnCategory] | None = None,
) -> RepositoryModel:
    """Look up a repository, verify it's scannable, and run its scan.

    `selected_categories=None` scans every category (the default);
    otherwise only the given categories are activated — see
    `core/heuristics/category_filter.py`.

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
    return run_scan(repository, session, llm_client, settings, selected_categories)


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
    repository: RepositoryModel,
    session: Session,
    llm_client: httpx.Client,
    settings: Settings,
    selected_categories: frozenset[VulnCategory] | None = None,
) -> RepositoryModel:
    """Run the full vulnerability scan for one repository.

    Replaces any prior findings for this repository — rescans overwrite,
    they don't accumulate (no scan-history table in v1).
    `selected_categories=None` scans every category; otherwise only the
    given categories are activated, and the dependency-manifest check
    (category `vulnerable_dependencies`) only runs when that category is
    selected.
    """
    update_repository_status(session, repository, RepositoryStatus.SCANNING)

    stored_files = list_stored_files_for_repository(session, repository.id)
    content_by_path = {file.relative_path: file.content or "" for file in stored_files}

    heuristic_results = _run_heuristics_over_files(stored_files, selected_categories)
    manifest_finding = (
        find_dependency_manifest([file.relative_path for file in stored_files])
        if selected_categories is None
        or VulnCategory.VULNERABLE_DEPENDENCIES in selected_categories
        else None
    )

    admitted, files_over_cap = cap_to_call_budget(
        heuristic_results, settings.max_llm_calls_per_scan
    )
    outcome = confirm_flagged_files(admitted, content_by_path, llm_client, settings)
    outcome.files_over_cap = files_over_cap
    if manifest_finding is not None:
        outcome.findings.append(manifest_finding)

    return _finalize_scan(session, repository, outcome)


def _run_heuristics_over_files(
    stored_files: list[RepositoryFileModel],
    selected_categories: frozenset[VulnCategory] | None,
) -> list[HeuristicScanResult]:
    results = []
    for file in stored_files:
        result = run_heuristics(file.relative_path, file.content or "")
        if result is None:
            continue
        filtered = filter_to_categories(result, selected_categories)
        if filtered is not None:
            results.append(filtered)
    return results


def _finalize_scan(
    session: Session, repository: RepositoryModel, outcome: ScanOutcome
) -> RepositoryModel:
    delete_findings_for_repository(session, repository.id)
    insert_findings(session, repository.id, outcome.findings)

    completion = derive_scan_completion(outcome)
    if completion.total_failure:
        return update_repository_scan_outcome(
            session,
            repository,
            status=RepositoryStatus.SCAN_FAILED,
            scan_incomplete=False,
            scan_incomplete_reason=None,
            scan_failure_reason=ScanFailureReason.LLM_UNAVAILABLE,
        )

    return update_repository_scan_outcome(
        session,
        repository,
        status=RepositoryStatus.SCANNED,
        scan_incomplete=completion.incomplete,
        scan_incomplete_reason=completion.incomplete_reason,
        scan_failure_reason=None,
    )
