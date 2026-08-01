"""Detects unsafe deserialization and XML parsing that may allow XXE.

Matches vuln-scan category 5 (XXE / insecure deserialization).
"""

import re

from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.vuln_category import VulnCategory

_UNSAFE_DESERIALIZATION = re.compile(
    r"\bpickle\.(loads?|Unpickler)\b|\bmarshal\.loads?\b|\byaml\.load\s*\((?!.*SafeLoader)"
)
_XML_PARSING = re.compile(r"\b(xml\.etree\.ElementTree|lxml\.etree|xml\.sax|xml\.dom\.minidom)\b")


def find_insecure_deserialization_hits(content: str) -> list[HeuristicHit]:
    """Find unsafe deserialization calls and XML parsers worth an XXE review."""
    hits = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if _UNSAFE_DESERIALIZATION.search(line) or _XML_PARSING.search(line):
            hits.append(
                HeuristicHit(
                    VulnCategory.XXE_INSECURE_DESERIALIZATION, line_number, line.strip()
                )
            )
    return hits
