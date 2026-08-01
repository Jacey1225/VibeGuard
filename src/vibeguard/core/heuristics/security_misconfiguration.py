"""Detects presence-based security misconfigurations.

Matches vuln-scan category 6 (security misconfiguration) — presence-
based signals only (debug mode, wildcard CORS, default credentials).
Absence-based checks (missing security headers) need to know what the
whole app does, not just one file, so they're out of scope for v1.
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_DEBUG_ENABLED = re.compile(r"\bDEBUG\s*=\s*True\b")
_CORS_WILDCARD = re.compile(
    r"""allow_origins\s*=\s*\[?\s*["']\*["']|"""
    r"""Access-Control-Allow-Origin["']?\s*[:=]\s*["']\*["']"""
)
_DEFAULT_CREDENTIALS = re.compile(
    r"""(?i)\b(password|passwd)\b\s*=\s*["'](admin|password|changeme|123456|root|guest)["']"""
)


def find_security_misconfiguration_hits(content: str) -> list[HeuristicHit]:
    """Find debug-mode flags, wildcard CORS, or default-credential literals."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if (
            _DEBUG_ENABLED.search(line)
            or _CORS_WILDCARD.search(line)
            or _DEFAULT_CREDENTIALS.search(line)
        ):
            hits.append(
                HeuristicHit(VulnCategory.SECURITY_MISCONFIGURATION, line_number, line.strip())
            )
    return hits
