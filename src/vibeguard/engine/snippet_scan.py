"""Top-level orchestration for a plain-text snippet vulnerability scan.

Sequence: run heuristics over the single submitted blob -> cap and
confirm via the LLM if flagged (see `engine/llm_confirmation.py`) ->
replace prior findings -> finalize status. No dependency-manifest check
here -- that heuristic looks for a manifest/lockfile *filename* across
a whole file tree, which doesn't apply to one pasted blob.
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.snippet_finding_model import SnippetFindingModel
from vibeguard.adapters.db.snippet_finding_store import (
    delete_findings_for_snippet,
    insert_snippet_findings,
    list_findings_for_snippet,
)
from vibeguard.adapters.db.snippet_model import SnippetModel
from vibeguard.adapters.db.snippet_store import (
    get_snippet_by_id,
    update_snippet_scan_outcome,
    update_snippet_status,
)
from vibeguard.core.heuristics.run_heuristics import run_heuristics
from vibeguard.core.repository_status import ScanFailureReason
from vibeguard.core.snippet_status import SnippetStatus
from vibeguard.engine.llm_confirmation import (
    ScanOutcome,
    cap_to_call_budget,
    confirm_flagged_files,
    derive_scan_completion,
)


class SnippetNotFoundError(RuntimeError):
    """Raised when a snippet id doesn't exist."""


class SnippetNotReadyForScanError(RuntimeError):
    """Raised when a snippet isn't in a status that allows scanning."""


_SCANNABLE_STATUSES = frozenset(
    {SnippetStatus.SCAN_PENDING, SnippetStatus.SCANNED, SnippetStatus.SCAN_FAILED}
)


def run_snippet_scan_for_id(
    snippet_id: int, session: Session, llm_client: httpx.Client, settings: Settings
) -> SnippetModel:
    """Look up a snippet, verify it's scannable, and run its scan.

    Raises:
        SnippetNotFoundError: no snippet with this id exists.
        SnippetNotReadyForScanError: the snippet's current status
            doesn't allow scanning (e.g. rejected during intake).
    """
    snippet = get_snippet_by_id(session, snippet_id)
    if snippet is None:
        raise SnippetNotFoundError(f"no snippet with id {snippet_id}")
    if snippet.status not in _SCANNABLE_STATUSES:
        raise SnippetNotReadyForScanError(
            f"snippet {snippet_id} has status {snippet.status.value}, not ready to scan"
        )
    return run_snippet_scan(snippet, session, llm_client, settings)


def get_findings_for_snippet(snippet_id: int, session: Session) -> list[SnippetFindingModel]:
    """Look up a snippet's findings, worst-first.

    Raises:
        SnippetNotFoundError: no snippet with this id exists.
    """
    snippet = get_snippet_by_id(session, snippet_id)
    if snippet is None:
        raise SnippetNotFoundError(f"no snippet with id {snippet_id}")
    return list_findings_for_snippet(session, snippet_id)


def run_snippet_scan(
    snippet: SnippetModel, session: Session, llm_client: httpx.Client, settings: Settings
) -> SnippetModel:
    """Run the full vulnerability scan for one plain-text snippet.

    Replaces any prior findings for this snippet -- rescans overwrite,
    they don't accumulate, the same rule repository rescans follow.
    """
    update_snippet_status(session, snippet, SnippetStatus.SCANNING)

    content = snippet.content or ""
    heuristic_result = run_heuristics(snippet.filename, content)
    heuristic_results = [heuristic_result] if heuristic_result is not None else []

    admitted, files_over_cap = cap_to_call_budget(
        heuristic_results, settings.max_llm_calls_per_scan
    )
    outcome = confirm_flagged_files(admitted, {snippet.filename: content}, llm_client, settings)
    outcome.files_over_cap = files_over_cap

    return _finalize_scan(session, snippet, outcome)


def _finalize_scan(session: Session, snippet: SnippetModel, outcome: ScanOutcome) -> SnippetModel:
    delete_findings_for_snippet(session, snippet.id)
    insert_snippet_findings(session, snippet.id, outcome.findings)

    completion = derive_scan_completion(outcome)
    if completion.total_failure:
        return update_snippet_scan_outcome(
            session,
            snippet,
            status=SnippetStatus.SCAN_FAILED,
            scan_incomplete=False,
            scan_incomplete_reason=None,
            scan_failure_reason=ScanFailureReason.LLM_UNAVAILABLE,
        )

    return update_snippet_scan_outcome(
        session,
        snippet,
        status=SnippetStatus.SCANNED,
        scan_incomplete=completion.incomplete,
        scan_incomplete_reason=completion.incomplete_reason,
        scan_failure_reason=None,
    )
