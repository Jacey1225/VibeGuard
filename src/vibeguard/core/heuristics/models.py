"""The shared result shape every heuristic pattern-matcher produces."""

from dataclasses import dataclass

from vibeguard.core.vuln_category import VulnCategory


@dataclass(frozen=True)
class HeuristicHit:
    """One heuristic match within a file's content.

    An internal candidate, not a persisted `Finding` — a hit only means
    "this line is worth an LLM's confirmation," not that a
    vulnerability was actually confirmed.
    """

    category: VulnCategory
    line_number: int
    matched_snippet: str
