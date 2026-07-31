"""Placeholder hook for the future vulnerability-scanning rule engine.

The real rule-checking logic (built against the `vuln-scan` skill's
OWASP-style checklist) is out of scope for the intake feature — this
stub only marks that a repository is ready for it.
"""

from sqlalchemy.orm import Session

from vibeguard.adapters.db.models import RepositoryModel
from vibeguard.adapters.db.repository_store import update_repository_status
from vibeguard.core.repository_status import RepositoryStatus


def mark_scan_pending_implementation(
    session: Session, repository: RepositoryModel
) -> RepositoryModel:
    """Flip a repository's status to indicate it's ready for a real scan."""
    return update_repository_status(
        session, repository, RepositoryStatus.SCAN_PENDING_IMPLEMENTATION
    )
