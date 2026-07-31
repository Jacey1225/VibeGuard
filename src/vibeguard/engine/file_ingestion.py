"""Sequencing the walk, filter, and read of one cloned repository's files."""

from pathlib import Path

from vibeguard.adapters.filesystem.file_read import (
    read_file_contents,
    read_file_sample,
    read_file_size,
)
from vibeguard.adapters.filesystem.path_containment import (
    PathEscapesCloneRootError,
    resolve_within_clone_root,
)
from vibeguard.adapters.filesystem.tree_walk import walk_clone_tree
from vibeguard.core.file_filter import (
    SkippedFile,
    StoredFile,
    exceeds_max_file_size,
    looks_binary,
)
from vibeguard.core.ingest_budget import IngestBudget, IngestSummary
from vibeguard.core.repository_status import SkipReason
from vibeguard.core.text_decode import decode_file_text

_TRUNCATING_SKIP_REASONS = (
    SkipReason.FILE_COUNT_LIMIT_EXCEEDED,
    SkipReason.TOTAL_SIZE_LIMIT_EXCEEDED,
)


def ingest_clone_tree(
    clone_root: Path, max_file_size_bytes: int, budget: IngestBudget
) -> IngestSummary:
    """Walk, filter, and read every file under `clone_root` into a summary."""
    resolved_root = clone_root.resolve()
    summary = IngestSummary()

    for candidate in walk_clone_tree(clone_root):
        fallback_relative_path = str(candidate.relative_to(clone_root))
        try:
            resolved = resolve_within_clone_root(clone_root, candidate)
        except PathEscapesCloneRootError:
            summary.skipped.append(SkippedFile(fallback_relative_path, 0, SkipReason.UNSAFE_PATH))
            continue

        relative_path = str(resolved.relative_to(resolved_root))
        outcome = ingest_single_file(resolved, relative_path, max_file_size_bytes, budget)
        _record_outcome(summary, outcome)

    return summary


def _record_outcome(summary: IngestSummary, outcome: StoredFile | SkippedFile) -> None:
    if isinstance(outcome, StoredFile):
        summary.stored.append(outcome)
        return
    summary.skipped.append(outcome)
    if outcome.skip_reason in _TRUNCATING_SKIP_REASONS:
        summary.files_truncated = True
        summary.truncation_reason = outcome.skip_reason.value


def ingest_single_file(
    path: Path, relative_path: str, max_file_size_bytes: int, budget: IngestBudget
) -> StoredFile | SkippedFile:
    """Classify one file and, if eligible under every limit, read its contents."""
    size_bytes = read_file_size(path)

    if exceeds_max_file_size(size_bytes, max_file_size_bytes):
        return SkippedFile(relative_path, size_bytes, SkipReason.TOO_LARGE)
    if not budget.has_file_count_capacity():
        return SkippedFile(relative_path, size_bytes, SkipReason.FILE_COUNT_LIMIT_EXCEEDED)
    if not budget.has_total_size_capacity(size_bytes):
        return SkippedFile(relative_path, size_bytes, SkipReason.TOTAL_SIZE_LIMIT_EXCEEDED)

    sample = read_file_sample(path)
    if looks_binary(sample):
        return SkippedFile(relative_path, size_bytes, SkipReason.BINARY)

    try:
        raw = read_file_contents(path, max_file_size_bytes)
    except ValueError:
        return SkippedFile(relative_path, size_bytes, SkipReason.TOO_LARGE)

    budget.record(size_bytes)
    return StoredFile(relative_path, size_bytes, decode_file_text(raw))
