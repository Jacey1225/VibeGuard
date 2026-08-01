"""A proposed code fix for one file's findings, before human review."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RemediationProposal:
    """One file's proposed fix, generated but not yet reviewed.

    `summary` is the model's own explanation of the fix, surfaced to the
    human reviewer as-is — this is also where category guidance (see
    `core/remediation_guidance/`) instructs the model to call out
    remaining manual follow-up it can't close by editing code alone
    (e.g. a hardcoded secret that must be rotated at the source, since
    removing it from the file doesn't invalidate it).

    `introduces_new_heuristic_hits`/`new_heuristic_hit_summary` are the
    safety-net result of re-running the heuristic layer against
    `proposed_content` — a signal for the human reviewer, not a gate.
    """

    relative_path: str
    original_content: str
    proposed_content: str
    diff_text: str
    summary: str
    model: str
    finding_ids: tuple[int, ...]
    introduces_new_heuristic_hits: bool
    new_heuristic_hit_summary: str | None
