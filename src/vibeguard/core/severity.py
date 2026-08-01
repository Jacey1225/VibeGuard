"""Finding severity scale.

Declared in ascending order deliberately: Postgres native enums sort by
declaration order, not alphabetically, so `ORDER BY severity DESC`
only means "worst first" because `CRITICAL` is declared last here.
Reordering this enum silently breaks every "worst first" query.
"""

from enum import StrEnum


class Severity(StrEnum):
    """How serious a finding is, low to high."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
