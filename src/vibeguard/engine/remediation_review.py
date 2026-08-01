"""Looking up a repository's remediations for human review."""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.remediation_model import RemediationModel
from vibeguard.adapters.db.remediation_store import list_remediations_for_repository
from vibeguard.adapters.db.repository_store import get_repository_by_id
from vibeguard.engine.vuln_scan import RepositoryNotFoundError


def get_remediations_for_repository(
    repository_id: int, session: Session
) -> list[RemediationModel]:
    """Look up a repository's remediations, newest first.

    Raises:
        RepositoryNotFoundError: no repository with this id exists.
    """
    repository = get_repository_by_id(session, repository_id)
    if repository is None:
        raise RepositoryNotFoundError(f"no repository with id {repository_id}")
    return list_remediations_for_repository(session, repository_id)
