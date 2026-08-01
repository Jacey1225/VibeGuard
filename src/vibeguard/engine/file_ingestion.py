"""Sequencing the walk, filter, and read of one cloned repository's files.

Split into three phases so the I/O-bound part (reading file contents)
can be parallelized without any shared mutable state: admission against
the aggregate budget is decided sequentially, in full, before any
content is read, so the concurrent read phase never has to coordinate
with anything else.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _FileCandidate:
    """A file that passed path-safety and individual-size checks, awaiting budget admission."""

    path: Path
    relative_path: str
    size_bytes: int


def ingest_clone_tree(
    clone_root: Path,
    max_file_size_bytes: int,
    budget: IngestBudget,
    thread_pool_size: int,
) -> IngestSummary:
    """Walk, filter, and read every file under `clone_root` into a summary."""
    candidates, pre_admission_skipped = stat_candidate_files(clone_root, max_file_size_bytes)
    admitted, budget_skipped = admit_candidates_within_budget(candidates, budget)
    read_outcomes = read_admitted_files_concurrently(
        admitted, max_file_size_bytes, thread_pool_size
    )

    summary = IngestSummary()
    for outcome in (*pre_admission_skipped, *budget_skipped, *read_outcomes):
        _record_outcome(summary, outcome)
    return summary


def stat_candidate_files(
    clone_root: Path, max_file_size_bytes: int
) -> tuple[list[_FileCandidate], list[SkippedFile]]:
    """Walk the tree, containing each path and checking its individual size.

    Path-safety and individual-file-size violations don't depend on how
    many other files have been admitted, so they're decided here,
    before the aggregate budget ever enters the picture.
    """
    resolved_root = clone_root.resolve()
    candidates: list[_FileCandidate] = []
    skipped: list[SkippedFile] = []

    for candidate_path in walk_clone_tree(clone_root):
        fallback_relative_path = str(candidate_path.relative_to(clone_root))
        try:
            resolved = resolve_within_clone_root(clone_root, candidate_path)
        except PathEscapesCloneRootError:
            skipped.append(SkippedFile(fallback_relative_path, 0, SkipReason.UNSAFE_PATH))
            continue

        relative_path = str(resolved.relative_to(resolved_root))
        size_bytes = read_file_size(resolved)
        if exceeds_max_file_size(size_bytes, max_file_size_bytes):
            skipped.append(SkippedFile(relative_path, size_bytes, SkipReason.TOO_LARGE))
            continue

        candidates.append(_FileCandidate(resolved, relative_path, size_bytes))

    return candidates, skipped


def admit_candidates_within_budget(
    candidates: list[_FileCandidate], budget: IngestBudget
) -> tuple[list[_FileCandidate], list[SkippedFile]]:
    """Apply the aggregate file-count/size budget to a pre-stated candidate list.

    Pure and sequential — runs to completion before any content is
    read, so admission is decided deterministically with no risk of a
    race once reading is parallelized. `IngestBudget` itself stays a
    plain, unlocked object because of this ordering.
    """
    admitted: list[_FileCandidate] = []
    skipped: list[SkippedFile] = []

    for candidate in candidates:
        if not budget.has_file_count_capacity():
            skipped.append(
                SkippedFile(
                    candidate.relative_path,
                    candidate.size_bytes,
                    SkipReason.FILE_COUNT_LIMIT_EXCEEDED,
                )
            )
            continue
        if not budget.has_total_size_capacity(candidate.size_bytes):
            skipped.append(
                SkippedFile(
                    candidate.relative_path,
                    candidate.size_bytes,
                    SkipReason.TOTAL_SIZE_LIMIT_EXCEEDED,
                )
            )
            continue
        budget.record(candidate.size_bytes)
        admitted.append(candidate)

    return admitted, skipped


def read_admitted_files_concurrently(
    admitted: list[_FileCandidate], max_file_size_bytes: int, thread_pool_size: int
) -> list[StoredFile | SkippedFile]:
    """Read, binary-sniff, and decode every admitted file's contents.

    The I/O-bound part of ingestion, parallelized: admission was
    already decided, so each file's read is fully independent of every
    other — no shared state, no locking.
    """
    if not admitted:
        return []
    with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
        return list(
            executor.map(
                lambda candidate: _read_one_admitted_file(candidate, max_file_size_bytes),
                admitted,
            )
        )


def _read_one_admitted_file(
    candidate: _FileCandidate, max_file_size_bytes: int
) -> StoredFile | SkippedFile:
    sample = read_file_sample(candidate.path)
    if looks_binary(sample):
        return SkippedFile(candidate.relative_path, candidate.size_bytes, SkipReason.BINARY)

    try:
        raw = read_file_contents(candidate.path, max_file_size_bytes)
    except ValueError:
        return SkippedFile(candidate.relative_path, candidate.size_bytes, SkipReason.TOO_LARGE)

    return StoredFile(candidate.relative_path, candidate.size_bytes, decode_file_text(raw))


def _record_outcome(summary: IngestSummary, outcome: StoredFile | SkippedFile) -> None:
    if isinstance(outcome, StoredFile):
        summary.stored.append(outcome)
        return
    summary.skipped.append(outcome)
    if outcome.skip_reason in _TRUNCATING_SKIP_REASONS:
        summary.files_truncated = True
        summary.truncation_reason = outcome.skip_reason.value
