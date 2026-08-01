"""Running every heuristic module over one file, deduped to one result."""

from dataclasses import dataclass

from vibeguard.core.heuristics.crypto_failures import find_crypto_failures_hits
from vibeguard.core.heuristics.entry_point import find_entry_point_hits
from vibeguard.core.heuristics.injection import find_injection_hits
from vibeguard.core.heuristics.insecure_deserialization import (
    find_insecure_deserialization_hits,
)
from vibeguard.core.heuristics.models import HeuristicHit
from vibeguard.core.heuristics.security_misconfiguration import (
    find_security_misconfiguration_hits,
)
from vibeguard.core.heuristics.ssrf import find_ssrf_hits
from vibeguard.core.heuristics.xss import find_xss_hits
from vibeguard.core.vuln_category import VulnCategory

_TIER_A_FINDERS = (
    find_injection_hits,
    find_crypto_failures_hits,
    find_insecure_deserialization_hits,
    find_security_misconfiguration_hits,
    find_xss_hits,
    find_ssrf_hits,
)


@dataclass(frozen=True)
class HeuristicScanResult:
    """Every category one file's content matched, deduped to one entry per file."""

    relative_path: str
    categories: tuple[VulnCategory, ...]
    hits: tuple[HeuristicHit, ...]


def run_heuristics(relative_path: str, content: str) -> HeuristicScanResult | None:
    """Run every heuristic module over one file's content.

    Returns `None` if nothing matched. Otherwise returns exactly one
    result per file, listing every matched category — this is what
    keeps the LLM to one call per flagged file regardless of how many
    categories it trips.
    """
    all_hits: list[HeuristicHit] = []
    for finder in _TIER_A_FINDERS:
        all_hits.extend(finder(content))
    all_hits.extend(find_entry_point_hits(content))

    if not all_hits:
        return None

    return HeuristicScanResult(
        relative_path=relative_path,
        categories=_dedupe_categories_in_order(all_hits),
        hits=tuple(all_hits),
    )


def _dedupe_categories_in_order(hits: list[HeuristicHit]) -> tuple[VulnCategory, ...]:
    seen: set[VulnCategory] = set()
    ordered: list[VulnCategory] = []
    for hit in hits:
        if hit.category not in seen:
            seen.add(hit.category)
            ordered.append(hit.category)
    return tuple(ordered)
