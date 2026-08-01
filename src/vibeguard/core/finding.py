"""A single vulnerability finding, and how it was produced."""

from dataclasses import dataclass
from enum import StrEnum

from vibeguard.core.severity import Severity
from vibeguard.core.vuln_category import VulnCategory


class FindingSource(StrEnum):
    """How a finding was produced."""

    HEURISTIC_ONLY = "heuristic_only"
    HEURISTIC_CONFIRMED = "heuristic_confirmed"


@dataclass(frozen=True)
class Finding:
    """One confirmed vulnerability in one file.

    `model` is which LLM produced this finding, if any — None for
    findings from `FindingSource.HEURISTIC_ONLY` (e.g. the dependency-
    manifest check, which never calls an LLM).
    """

    category: VulnCategory
    severity: Severity
    title: str
    description: str
    remediation: str
    relative_path: str
    line_number: int | None
    source: FindingSource
    model: str | None = None
