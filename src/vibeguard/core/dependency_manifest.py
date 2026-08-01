"""Detects dependency manifest/lockfile presence for a repository.

Matches vuln-scan category 9 (vulnerable dependencies) honestly: this
doesn't identify actual CVEs (that needs a real SCA tool, e.g.
pip-audit/npm audit/osv-scanner) — it confirms a manifest exists and
points at one as a follow-up, closing the checklist item rather than
silently dropping it.
"""

from pathlib import Path

from vibeguard.core.finding import Finding, FindingSource
from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory

_MANIFEST_FILENAMES = frozenset(
    {
        "requirements.txt",
        "pyproject.toml",
        "Pipfile.lock",
        "poetry.lock",
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "go.sum",
        "Gemfile.lock",
        "composer.lock",
        "Cargo.lock",
    }
)


def find_dependency_manifest(relative_paths: list[str]) -> Finding | None:
    """Return an informational finding if any dependency manifest/lockfile is present."""
    matched = next(
        (path for path in relative_paths if Path(path).name in _MANIFEST_FILENAMES), None
    )
    if matched is None:
        return None

    return Finding(
        category=VulnCategory.VULNERABLE_DEPENDENCIES,
        severity=Severity.INFO,
        title="Dependency manifest present — run a dedicated SCA scan",
        description=(
            f"Found a dependency manifest/lockfile ({matched}). VibeGuard doesn't "
            "match dependency versions against known CVEs — run pip-audit, "
            "npm audit, or osv-scanner against this manifest for real "
            "vulnerability data."
        ),
        remediation=(
            "Run a dedicated software-composition-analysis tool (pip-audit for "
            "Python, npm audit / yarn audit for Node, osv-scanner for "
            "multi-ecosystem) against this manifest and update any flagged "
            "dependencies."
        ),
        relative_path=matched,
        line_number=None,
        source=FindingSource.HEURISTIC_ONLY,
    )
