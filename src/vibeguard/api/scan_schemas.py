"""The shared request body for triggering a scan, by repository or by snippet."""

from pydantic import BaseModel, Field, field_validator

from vibeguard.core.vuln_category import VulnCategory


class ScanRequest(BaseModel):
    """The optional body of a `POST .../scan` request.

    `categories=None` (the default — an omitted body scans exactly the
    same way) means every category is scanned, matching the pre-existing
    behavior. An explicit empty list is rejected rather than silently
    scanning nothing, since that's far more likely a client mistake than
    an intentional "scan for nothing" request.
    """

    categories: list[VulnCategory] | None = Field(
        None, description="Which vulnerability categories to scan for. Omit to scan all."
    )

    @field_validator("categories")
    @classmethod
    def _reject_empty_list(cls, value: list[VulnCategory] | None) -> list[VulnCategory] | None:
        if value is not None and len(value) == 0:
            raise ValueError("categories must be non-empty if provided; omit it to scan all")
        return value

    def selected_categories(self) -> frozenset[VulnCategory] | None:
        """The requested categories as a set for O(1) membership checks, or `None` for "all"."""
        if self.categories is None:
            return None
        return frozenset(self.categories)
