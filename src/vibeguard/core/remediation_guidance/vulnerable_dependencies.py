"""Remediation guidance for vulnerable/outdated dependencies.

VibeGuard's own dependency finding is a `HEURISTIC_ONLY` presence check,
never LLM-generated (see `core/dependency_manifest.py`) — this module
exists for completeness of the guidance library (every `VulnCategory`
has an entry, verified by a test) rather than because a remediation LLM
call is ever actually made for this category today.
"""

GUIDANCE = (
    "Do not attempt to guess which dependency versions are vulnerable or "
    "hand-pick replacement version numbers -- run a dedicated "
    "software-composition-analysis tool (pip-audit, npm audit / yarn "
    "audit, osv-scanner) against the manifest and update only the "
    "versions it flags, to the versions it recommends."
)
