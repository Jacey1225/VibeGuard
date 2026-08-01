"""Broad detection of files shaped like routes, auth, or error handling.

Tier B: unlike the Tier-A category modules, this doesn't try to pin a
specific vulnerability to a specific line — a match here means "this
file is shaped like an entry point," which is enough to justify sending
it to the LLM for a combined review of broken auth (category 2), broken
access control (category 3), and insufficient logging (category 10)
together, rather than building three separate narrow heuristics.
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_ENTRY_POINT_SIGNAL = re.compile(
    r"""@(?:app|router)\.(?:get|post|put|delete|patch|route)\s*\(|"""
    r"""\bdef\s+(?:login|logout|authenticate|authorize)\b|"""
    r"""class\s+\w*(?:View|Handler|Controller)\b|"""
    r"""@(?:login_required|permission_required)\b|"""
    r"""\bexcept\s+\w*Error\b"""
)

_ENTRY_POINT_CATEGORIES = (
    VulnCategory.BROKEN_AUTH,
    VulnCategory.BROKEN_ACCESS_CONTROL,
    VulnCategory.INSUFFICIENT_LOGGING,
)


def find_entry_point_hits(content: str) -> list[HeuristicHit]:
    """Find the first entry-point-shaped line, tagged with all three Tier-B categories.

    Only the first match matters — one signal is enough to justify a
    single combined LLM review of this file.
    """
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _ENTRY_POINT_SIGNAL.search(line):
            snippet = line.strip()
            return [
                HeuristicHit(category, line_number, snippet)
                for category in _ENTRY_POINT_CATEGORIES
            ]
    return []
