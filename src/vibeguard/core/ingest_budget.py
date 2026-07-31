"""Aggregate resource-budget tracking across an entire repository ingest."""

from dataclasses import dataclass, field

from vibeguard.core.file_filter import SkippedFile, StoredFile


@dataclass
class IngestBudget:
    """Running totals against the aggregate file-count/size limits."""

    max_file_count: int
    max_total_bytes: int
    file_count: int = 0
    total_bytes: int = 0

    def has_file_count_capacity(self) -> bool:
        """Return whether one more file can be recorded under the count limit."""
        return self.file_count < self.max_file_count

    def has_total_size_capacity(self, additional_bytes: int) -> bool:
        """Return whether adding `additional_bytes` stays under the size limit."""
        return self.total_bytes + additional_bytes <= self.max_total_bytes

    def record(self, size_bytes: int) -> None:
        """Record that one more file of `size_bytes` was stored."""
        self.file_count += 1
        self.total_bytes += size_bytes


@dataclass
class IngestSummary:
    """The outcome of walking and filtering one repository's file tree."""

    stored: list[StoredFile] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    files_truncated: bool = False
    truncation_reason: str | None = None
