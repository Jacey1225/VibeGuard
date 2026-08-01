"""Mapping a StrEnum's values (not names) onto a Postgres native enum column.

SQLAlchemy's `Enum` type persists a Python enum member's *name* by
default, not its `.value` — since every VibeGuard StrEnum's member
names are uppercase and values are lowercase, every enum-typed column
must pass this as `values_callable` or the database ends up storing
`"PENDING"` instead of `"pending"`.
"""

from enum import StrEnum


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Return a StrEnum's member values, in declaration order."""
    return [member.value for member in enum_cls]
