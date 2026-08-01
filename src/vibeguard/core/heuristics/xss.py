"""Detects unescaped output sinks that may allow cross-site scripting.

Matches vuln-scan category 7 (XSS).
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_XSS_SINK = re.compile(
    r"dangerouslySetInnerHTML|\.innerHTML\s*=|v-html\s*=|\|\s*safe\b|\bMarkup\s*\("
)


def find_xss_hits(content: str) -> list[HeuristicHit]:
    """Find unescaped-output sinks worth an XSS review."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _XSS_SINK.search(line):
            hits.append(HeuristicHit(VulnCategory.XSS, line_number, line.strip()))
    return hits
