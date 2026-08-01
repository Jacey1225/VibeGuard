"""Detects hardcoded secrets and weak cryptographic/TLS configuration.

Matches vuln-scan category 4 (cryptographic failures) — secrets and
weak crypto are grouped in one module since they're the same checklist
category, not split per specific pattern.
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_SECRET_ASSIGNMENT = re.compile(
    r"""(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*=\s*["'][A-Za-z0-9_\-/+=]{8,}["']"""
)
_DISABLED_TLS_VERIFY = re.compile(
    r"""verify\s*=\s*False|CERT_NONE|_create_unverified_context|"""
    r"""NODE_TLS_REJECT_UNAUTHORIZED["']?\s*[:=]\s*["']?0"""
)
_WEAK_ALGORITHM = re.compile(
    r"\b(hashlib\.md5|hashlib\.sha1|Crypto\.Cipher\.(DES|ARC4)|DES\.new)\b"
)

_ENV_LOOKUP_MARKERS = ("os.environ", "getenv", "os.environ.get")


def find_crypto_failures_hits(content: str) -> list[HeuristicHit]:
    """Find hardcoded secrets, disabled TLS verification, or weak algorithms."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _SECRET_ASSIGNMENT.search(line) and not any(
            marker in line for marker in _ENV_LOOKUP_MARKERS
        ):
            hits.append(HeuristicHit(VulnCategory.CRYPTO_FAILURES, line_number, line.strip()))
        elif _DISABLED_TLS_VERIFY.search(line):
            hits.append(HeuristicHit(VulnCategory.CRYPTO_FAILURES, line_number, line.strip()))
        elif _WEAK_ALGORITHM.search(line):
            hits.append(HeuristicHit(VulnCategory.CRYPTO_FAILURES, line_number, line.strip()))
    return hits
