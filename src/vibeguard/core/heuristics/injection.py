"""Detects SQL built via string concatenation or f-string interpolation.

Matches vuln-scan category 1 (injection). Deliberately narrow: only
flags queries built inline next to a `.execute(`/`.executemany(` call —
parameterized queries (`execute(query, params)`) don't match.
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_SQL_KEYWORD = r"(?:SELECT|INSERT|UPDATE|DELETE|DROP|WHERE)"

_FSTRING_QUERY = re.compile(
    rf"""\.execute(?:many)?\s*\(\s*f["'][^"']*{_SQL_KEYWORD}""", re.IGNORECASE
)
_CONCATENATED_QUERY = re.compile(
    rf"""\.execute(?:many)?\s*\([^)]*{_SQL_KEYWORD}[^)]*\+""", re.IGNORECASE
)


def find_injection_hits(content: str) -> list[HeuristicHit]:
    """Find lines that build a SQL query via f-string or `+` concatenation."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _FSTRING_QUERY.search(line) or _CONCATENATED_QUERY.search(line):
            hits.append(HeuristicHit(VulnCategory.INJECTION, line_number, line.strip()))
    return hits
