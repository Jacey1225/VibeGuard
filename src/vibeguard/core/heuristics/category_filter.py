"""Narrowing a heuristic result down to a caller-selected set of categories."""

from vibeguard.core.heuristics.run_heuristics import (
    HeuristicScanResult,
    dedupe_categories_in_order,
)
from vibeguard.core.vuln_category import VulnCategory


def filter_to_categories(
    result: HeuristicScanResult, selected_categories: frozenset[VulnCategory] | None
) -> HeuristicScanResult | None:
    """Restrict a heuristic result to only the selected categories.

    `selected_categories=None` means no filter is applied — `result` is
    returned unchanged, which is what "scan every category" (the
    default) needs. If filtering leaves no hits at all, returns `None`
    so the caller treats this file exactly as if nothing had matched in
    the first place — it never reaches the LLM confirmation step or the
    call-budget cap.
    """
    if selected_categories is None:
        return result

    kept_hits = tuple(hit for hit in result.hits if hit.category in selected_categories)
    if not kept_hits:
        return None

    return HeuristicScanResult(
        relative_path=result.relative_path,
        categories=dedupe_categories_in_order(list(kept_hits)),
        hits=kept_hits,
    )
