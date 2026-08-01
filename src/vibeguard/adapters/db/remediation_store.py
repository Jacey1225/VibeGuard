"""Persistence operations for proposed remediations and their decisions."""

from datetime import datetime

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from vibeguard.adapters.db.remediation_model import RemediationFindingModel, RemediationModel
from vibeguard.core.remediation import RemediationProposal
from vibeguard.core.remediation_status import PushFailureReason, RemediationStatus


def insert_remediation(
    session: Session, repository_id: int, proposal: RemediationProposal
) -> RemediationModel:
    """Persist a newly generated proposal and link it to the findings it addresses."""
    remediation = RemediationModel(
        repository_id=repository_id,
        relative_path=proposal.relative_path,
        status=RemediationStatus.PROPOSED,
        original_content=proposal.original_content,
        proposed_content=proposal.proposed_content,
        diff_text=proposal.diff_text,
        summary=proposal.summary,
        model=proposal.model,
        introduces_new_heuristic_hits=proposal.introduces_new_heuristic_hits,
        new_heuristic_hit_summary=proposal.new_heuristic_hit_summary,
    )
    session.add(remediation)
    session.flush()
    _link_remediation_findings(session, remediation.id, proposal.finding_ids)
    return remediation


def _link_remediation_findings(
    session: Session, remediation_id: int, finding_ids: tuple[int, ...]
) -> None:
    """Bulk-insert the join rows for one remediation's addressed findings.

    A single bulk `INSERT` covering all rows, not a per-finding loop
    with per-row round trips (search-sort-efficiency).
    """
    if not finding_ids:
        return
    rows = [
        {"remediation_id": remediation_id, "finding_id": finding_id} for finding_id in finding_ids
    ]
    session.execute(insert(RemediationFindingModel), rows)


def get_remediation_by_id(session: Session, remediation_id: int) -> RemediationModel | None:
    """Fetch a remediation by id, or `None` if it doesn't exist."""
    return session.get(RemediationModel, remediation_id)


def list_remediations_for_repository(
    session: Session, repository_id: int
) -> list[RemediationModel]:
    """Fetch every remediation for a repository, newest first.

    Ordered `created_at DESC` with an `id DESC` tiebreak for
    deterministic ordering when two rows share a timestamp, per
    search-sort-efficiency's explicit tie-break rule.
    """
    statement = (
        select(RemediationModel)
        .where(RemediationModel.repository_id == repository_id)
        .order_by(RemediationModel.created_at.desc(), RemediationModel.id.desc())
    )
    return list(session.execute(statement).scalars().all())


def record_remediation_rejection(
    session: Session,
    remediation: RemediationModel,
    decided_by_user_id: int,
    decided_at: datetime,
    decision_reason: str | None,
) -> RemediationModel:
    """Mark a remediation rejected by a reviewer."""
    remediation.status = RemediationStatus.REJECTED
    remediation.decided_by_user_id = decided_by_user_id
    remediation.decided_at = decided_at
    remediation.decision_reason = decision_reason
    session.flush()
    return remediation


def record_remediation_push_success(
    session: Session,
    remediation: RemediationModel,
    decided_by_user_id: int,
    decided_at: datetime,
    push_target_branch: str | None,
    pushed_commit_sha: str,
) -> RemediationModel:
    """Mark a remediation approved and successfully pushed to GitHub."""
    remediation.status = RemediationStatus.PUSHED
    remediation.decided_by_user_id = decided_by_user_id
    remediation.decided_at = decided_at
    remediation.push_target_branch = push_target_branch
    remediation.pushed_commit_sha = pushed_commit_sha
    remediation.push_failure_reason = None
    session.flush()
    return remediation


def record_remediation_push_failure(
    session: Session,
    remediation: RemediationModel,
    decided_by_user_id: int,
    decided_at: datetime,
    push_target_branch: str | None,
    push_failure_reason: PushFailureReason,
) -> RemediationModel:
    """Mark a remediation approved but failed to push, and why.

    `push_failed` is a retryable status (unlike `pushed`/`rejected`) —
    re-approving re-runs the push flow from scratch with fresh branch
    and file-sha fetches.
    """
    remediation.status = RemediationStatus.PUSH_FAILED
    remediation.decided_by_user_id = decided_by_user_id
    remediation.decided_at = decided_at
    remediation.push_target_branch = push_target_branch
    remediation.push_failure_reason = push_failure_reason
    session.flush()
    return remediation
