"""Detects outbound requests built from an interpolated or concatenated URL.

Matches vuln-scan category 8 (SSRF).
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_REQUEST_CALL = r"(?:requests|httpx)\.(?:get|post|put|delete|patch)|urllib\.request\.urlopen"
_FSTRING_URL = re.compile(rf"""(?:{_REQUEST_CALL})\s*\(\s*f["']""")
_CONCATENATED_URL = re.compile(rf"""(?:{_REQUEST_CALL})\s*\([^)]*\+""")


def find_ssrf_hits(content: str) -> list[HeuristicHit]:
    """Find outbound requests whose URL is built from an f-string or concatenation."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _FSTRING_URL.search(line) or _CONCATENATED_URL.search(line):
            hits.append(HeuristicHit(VulnCategory.SSRF, line_number, line.strip()))
    return hits
