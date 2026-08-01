"""Top-level orchestration for generating remediations from a repository's findings.

Sequence: verify the repository has a completed scan -> group findings
by file (one pass) -> cap and generate fixes via the LLM (bounded
concurrency, same admit-before-parallelize/ThreadPoolExecutor shape as
`engine/vuln_scan.py`) -> diff + heuristic safety net each result ->
persist. Every per-file LLM call is a fresh, independent request, same
reasoning as the scan engine.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import httpx
from sqlalchemy.orm import Session

from vibeguard.adapters.config.settings import Settings
from vibeguard.adapters.db.finding_model import FindingModel
from vibeguard.adapters.db.finding_store import list_stored_files_for_repository
from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.remediation_model import RemediationModel
from vibeguard.adapters.db.remediation_store import insert_remediation
from vibeguard.adapters.db.repository_store import get_repository_by_id
from vibeguard.adapters.llm.remediation_client import (
    GeneratedRemediation,
    RemediationResponseParseError,
    RemediationUnavailableError,
    generate_remediation,
)
from vibeguard.core.diff import compute_unified_diff
from vibeguard.core.finding import Finding
from vibeguard.core.heuristics.run_heuristics import run_heuristics
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.repository_status import RepositoryStatus
from vibeguard.core.vuln_category import VulnCategory
from vibeguard.engine.vuln_scan import RepositoryNotFoundError, get_findings_for_repository

logger = logging.getLogger(__name__)


class RepositoryNotReadyForRemediationError(RuntimeError):
    """Raised when a repository hasn't completed a scan yet."""


@dataclass
class RemediationGenerationOutcome:
    """Counts and rows from one generation run, for the API response."""

    remediations: list[RemediationModel] = field(default_factory=list)
    attempted: int = 0
    succeeded: int = 0
    files_over_cap: int = 0


@dataclass(frozen=True)
class _FileFindingGroup:
    """One file's findings, grouped for a single generation call."""

    relative_path: str
    findings: tuple[FindingModel, ...]


def generate_remediations_for_repository(
    repository_id: int, session: Session, llm_client: httpx.Client, settings: Settings
) -> RemediationGenerationOutcome:
    """Look up a repository, verify it's scanned, and generate remediations for its findings.

    Raises:
        RepositoryNotFoundError: no repository with this id exists.
        RepositoryNotReadyForRemediationError: the repository hasn't
            completed a scan (`SCANNED` status).
    """
    repository = get_repository_by_id(session, repository_id)
    if repository is None:
        raise RepositoryNotFoundError(f"no repository with id {repository_id}")
    if repository.status != RepositoryStatus.SCANNED:
        raise RepositoryNotReadyForRemediationError(
            f"repository {repository_id} has status {repository.status.value}, "
            "not ready for remediation"
        )
    return _generate_remediations(repository, session, llm_client, settings)


def _generate_remediations(
    repository: RepositoryModel, session: Session, llm_client: httpx.Client, settings: Settings
) -> RemediationGenerationOutcome:
    findings = get_findings_for_repository(repository.id, session)
    groups = _group_findings_by_file(findings)
    if not groups:
        return RemediationGenerationOutcome()

    stored_files = list_stored_files_for_repository(session, repository.id)
    content_by_path = {file.relative_path: file.content or "" for file in stored_files}

    admitted, files_over_cap = _cap_to_call_budget(groups, settings.max_llm_calls_per_remediation)
    proposals = _generate_flagged_files(admitted, content_by_path, llm_client, settings)

    remediations = [
        insert_remediation(session, repository.id, proposal) for proposal in proposals
    ]
    return RemediationGenerationOutcome(
        remediations=remediations,
        attempted=len(admitted),
        succeeded=len(proposals),
        files_over_cap=files_over_cap,
    )


def _group_findings_by_file(findings: list[FindingModel]) -> list[_FileFindingGroup]:
    """Group findings by file in one pass, preserving each file's first-seen order."""
    findings_by_path: dict[str, list[FindingModel]] = {}
    for finding in findings:
        findings_by_path.setdefault(finding.relative_path, []).append(finding)
    return [
        _FileFindingGroup(relative_path=path, findings=tuple(group))
        for path, group in findings_by_path.items()
    ]


def _cap_to_call_budget(
    groups: list[_FileFindingGroup], max_calls: int
) -> tuple[list[_FileFindingGroup], int]:
    """Admit at most `max_calls` file groups, decided upfront.

    Same admit-before-parallelize pattern as `vuln_scan._cap_to_call_budget`
    — the full admitted set is decided before any concurrent work starts,
    so the cap needs no lock to stay race-free.
    """
    if len(groups) <= max_calls:
        return groups, 0
    return groups[:max_calls], len(groups) - max_calls


def _generate_flagged_files(
    admitted: list[_FileFindingGroup],
    content_by_path: dict[str, str],
    llm_client: httpx.Client,
    settings: Settings,
) -> list[RemediationProposal]:
    if not admitted:
        return []

    with ThreadPoolExecutor(max_workers=settings.max_concurrent_remediation_llm_calls) as executor:
        results = list(
            executor.map(
                lambda group: _generate_one_file(group, content_by_path, llm_client, settings),
                admitted,
            )
        )
    return [proposal for proposal in results if proposal is not None]


def _generate_one_file(
    group: _FileFindingGroup,
    content_by_path: dict[str, str],
    llm_client: httpx.Client,
    settings: Settings,
) -> RemediationProposal | None:
    """Generate one file's fix. Returns `None` on failure (logged, not raised)."""
    content = content_by_path.get(group.relative_path)
    if content is None:
        logger.warning(
            "remediation skipped, no stored content for %s", group.relative_path
        )
        return None

    core_findings = [_to_core_finding(finding) for finding in group.findings]
    try:
        generated = generate_remediation(
            group.relative_path,
            content,
            core_findings,
            llm_client,
            settings.openrouter_api_key,
            settings.openrouter_model,
            settings.llm_request_timeout_seconds,
            settings.remediation_llm_max_tokens,
        )
    except (RemediationUnavailableError, RemediationResponseParseError) as error:
        # Error type only -- never the exception's full message, which
        # can echo back response content (code-security: no full
        # payloads in logs, even on failure).
        logger.warning(
            "remediation generation failed for %s: %s", group.relative_path, type(error).__name__
        )
        return None

    return _to_remediation_proposal(group, content, generated)


def _to_core_finding(finding: FindingModel) -> Finding:
    return Finding(
        category=finding.category,
        severity=finding.severity,
        title=finding.title,
        description=finding.description,
        remediation=finding.remediation,
        relative_path=finding.relative_path,
        line_number=finding.line_number,
        source=finding.source,
        model=finding.model,
    )


def _to_remediation_proposal(
    group: _FileFindingGroup, original_content: str, generated: GeneratedRemediation
) -> RemediationProposal:
    diff_text = compute_unified_diff(
        original_content, generated.proposed_content, group.relative_path
    )
    introduces_new_hits, new_hits_summary = _run_safety_net(group, generated.proposed_content)
    return RemediationProposal(
        relative_path=group.relative_path,
        original_content=original_content,
        proposed_content=generated.proposed_content,
        diff_text=diff_text,
        summary=generated.summary,
        model=group.findings[0].model or "unknown",
        finding_ids=tuple(finding.id for finding in group.findings),
        introduces_new_heuristic_hits=introduces_new_hits,
        new_heuristic_hit_summary=new_hits_summary,
    )


def _run_safety_net(group: _FileFindingGroup, proposed_content: str) -> tuple[bool, str | None]:
    """Re-run heuristics against the proposed content, flagging any newly-introduced category.

    A signal for the human reviewer, not a gate — never blocks proposal
    creation. Must degrade gracefully: any exception here is swallowed
    and treated as "no new hits," never as a generation failure.
    """
    try:
        addressed_categories: set[VulnCategory] = {
            finding.category for finding in group.findings
        }
        result = run_heuristics(group.relative_path, proposed_content)
        if result is None:
            return False, None
        new_categories = set(result.categories) - addressed_categories
        if not new_categories:
            return False, None
        summary = "proposed fix newly triggered: " + ", ".join(
            sorted(category.value for category in new_categories)
        )
        return True, summary
    except Exception:  # must degrade gracefully -- never fail generation on this
        logger.warning("heuristic safety net failed for %s", group.relative_path)
        return False, None
