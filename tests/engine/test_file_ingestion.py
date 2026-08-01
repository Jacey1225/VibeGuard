"""Tests for walking, filtering, and reading a cloned repository's files."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import vibeguard.engine.file_ingestion as file_ingestion_module
from vibeguard.adapters.filesystem.path_containment import PathEscapesCloneRootError
from vibeguard.core.file_filter import SkippedFile, StoredFile
from vibeguard.core.ingest_budget import IngestBudget
from vibeguard.core.repository_status import SkipReason
from vibeguard.engine.file_ingestion import (
    _FileCandidate,
    _read_one_admitted_file,
    admit_candidates_within_budget,
    ingest_clone_tree,
    read_admitted_files_concurrently,
    stat_candidate_files,
)

_POOL_SIZE = 4


# ---- stat_candidate_files ----


def test_stat_candidate_files_creates_candidate_for_normal_file(tmp_path: Path):
    (tmp_path / "a.py").write_text("print(1)")

    candidates, skipped = stat_candidate_files(tmp_path, max_file_size_bytes=1000)

    assert skipped == []
    assert len(candidates) == 1
    assert candidates[0].relative_path == "a.py"
    assert candidates[0].size_bytes == len("print(1)")


def test_stat_candidate_files_skips_oversized_file(tmp_path: Path):
    (tmp_path / "big.py").write_bytes(b"x" * 2000)

    candidates, skipped = stat_candidate_files(tmp_path, max_file_size_bytes=1000)

    assert candidates == []
    assert len(skipped) == 1
    assert skipped[0].skip_reason == SkipReason.TOO_LARGE


def test_stat_candidate_files_skips_unsafe_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "suspicious.py").write_text("x")

    def _always_escapes(clone_root: Path, candidate: Path) -> Path:
        raise PathEscapesCloneRootError("forced for test")

    monkeypatch.setattr(file_ingestion_module, "resolve_within_clone_root", _always_escapes)

    candidates, skipped = stat_candidate_files(tmp_path, max_file_size_bytes=1000)

    assert candidates == []
    assert len(skipped) == 1
    assert skipped[0].skip_reason == SkipReason.UNSAFE_PATH


# ---- admit_candidates_within_budget ----


def _candidate(path: Path, relative_path: str, size_bytes: int) -> _FileCandidate:
    return _FileCandidate(path=path, relative_path=relative_path, size_bytes=size_bytes)


def test_admit_candidates_within_budget_admits_and_records(tmp_path: Path):
    candidates = [_candidate(tmp_path / "a.py", "a.py", 10)]
    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)

    admitted, skipped = admit_candidates_within_budget(candidates, budget)

    assert admitted == candidates
    assert skipped == []
    assert budget.file_count == 1
    assert budget.total_bytes == 10


def test_admit_candidates_within_budget_skips_when_file_count_exhausted(tmp_path: Path):
    candidates = [_candidate(tmp_path / "a.py", "a.py", 10)]
    budget = IngestBudget(max_file_count=1, max_total_bytes=1_000_000, file_count=1)

    admitted, skipped = admit_candidates_within_budget(candidates, budget)

    assert admitted == []
    assert skipped[0].skip_reason == SkipReason.FILE_COUNT_LIMIT_EXCEEDED


def test_admit_candidates_within_budget_skips_when_total_size_exhausted(tmp_path: Path):
    candidates = [_candidate(tmp_path / "a.py", "a.py", 50)]
    budget = IngestBudget(max_file_count=100, max_total_bytes=100, total_bytes=90)

    admitted, skipped = admit_candidates_within_budget(candidates, budget)

    assert admitted == []
    assert skipped[0].skip_reason == SkipReason.TOTAL_SIZE_LIMIT_EXCEEDED


def test_admit_candidates_within_budget_stops_admitting_once_full(tmp_path: Path):
    candidates = [
        _candidate(tmp_path / "a.py", "a.py", 10),
        _candidate(tmp_path / "b.py", "b.py", 10),
        _candidate(tmp_path / "c.py", "c.py", 10),
    ]
    budget = IngestBudget(max_file_count=2, max_total_bytes=1_000_000)

    admitted, skipped = admit_candidates_within_budget(candidates, budget)

    assert [c.relative_path for c in admitted] == ["a.py", "b.py"]
    assert skipped[0].relative_path == "c.py"
    assert skipped[0].skip_reason == SkipReason.FILE_COUNT_LIMIT_EXCEEDED


# ---- _read_one_admitted_file ----


def test_read_one_admitted_file_stores_text_content(tmp_path: Path):
    path = tmp_path / "a.py"
    path.write_text("print(1)")
    candidate = _candidate(path, "a.py", path.stat().st_size)

    outcome = _read_one_admitted_file(candidate, max_file_size_bytes=1000)

    assert isinstance(outcome, StoredFile)
    assert outcome.content == "print(1)"


def test_read_one_admitted_file_skips_binary(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01\x02binary")
    candidate = _candidate(path, "data.bin", path.stat().st_size)

    outcome = _read_one_admitted_file(candidate, max_file_size_bytes=1000)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.BINARY


def test_read_one_admitted_file_skips_when_content_exceeds_bound_toctou(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Simulates a file that grew between the size check and the read
    # (TOCTOU): read_file_contents' defensive bound still catches it.
    path = tmp_path / "a.py"
    path.write_text("x")
    candidate = _candidate(path, "a.py", path.stat().st_size)

    def _raise_value_error(path: Path, max_bytes: int) -> bytes:
        raise ValueError("grew after the size check")

    monkeypatch.setattr(file_ingestion_module, "read_file_contents", _raise_value_error)

    outcome = _read_one_admitted_file(candidate, max_file_size_bytes=1000)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.TOO_LARGE


# ---- read_admitted_files_concurrently ----


def test_read_admitted_files_concurrently_empty_list_returns_empty():
    assert read_admitted_files_concurrently([], max_file_size_bytes=1000, thread_pool_size=4) == []


def test_read_admitted_files_concurrently_preserves_input_order(tmp_path: Path):
    candidates = []
    for i in range(20):
        path = tmp_path / f"file{i}.py"
        path.write_text(f"content-{i}")
        candidates.append(_candidate(path, f"file{i}.py", path.stat().st_size))

    outcomes = read_admitted_files_concurrently(
        candidates, max_file_size_bytes=1000, thread_pool_size=_POOL_SIZE
    )

    assert [o.relative_path for o in outcomes] == [c.relative_path for c in candidates]
    assert all(isinstance(o, StoredFile) for o in outcomes)


def test_read_admitted_files_concurrently_uses_configured_pool_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "a.py"
    path.write_text("x")
    candidates = [_candidate(path, "a.py", path.stat().st_size)]

    seen_max_workers = []
    real_init = ThreadPoolExecutor.__init__

    def _tracking_init(self, *args, **kwargs):
        seen_max_workers.append(kwargs.get("max_workers", args[0] if args else None))
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(ThreadPoolExecutor, "__init__", _tracking_init)

    read_admitted_files_concurrently(candidates, max_file_size_bytes=1000, thread_pool_size=7)

    assert seen_max_workers == [7]


# ---- ingest_clone_tree (end-to-end) ----


def test_ingest_clone_tree_stores_and_skips_correctly(tmp_path: Path):
    (tmp_path / "keep.py").write_text("print('hi')")
    (tmp_path / "too_big.py").write_bytes(b"x" * 2000)
    (tmp_path / "binary.bin").write_bytes(b"\x00binary")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("should never be seen")

    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(
        tmp_path, max_file_size_bytes=1000, budget=budget, thread_pool_size=_POOL_SIZE
    )

    stored_paths = {f.relative_path for f in summary.stored}
    skipped_paths = {f.relative_path for f in summary.skipped}
    assert stored_paths == {"keep.py"}
    assert skipped_paths == {"too_big.py", "binary.bin"}
    assert summary.files_truncated is False


def test_ingest_clone_tree_marks_truncation_when_file_count_exceeded(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"file{i}.py").write_text("x")

    budget = IngestBudget(max_file_count=2, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(
        tmp_path, max_file_size_bytes=1000, budget=budget, thread_pool_size=_POOL_SIZE
    )

    assert len(summary.stored) == 2
    assert len(summary.skipped) == 3
    assert summary.files_truncated is True
    assert summary.truncation_reason == SkipReason.FILE_COUNT_LIMIT_EXCEEDED.value


def test_ingest_clone_tree_records_path_escape_as_skipped_not_a_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # tree_walk already skips symlinked files outright, so the escape
    # guard in resolve_within_clone_root is a defense-in-depth backstop
    # that's hard to trigger through the walk itself -- exercise it
    # directly by forcing the guard to fire for this file.
    (tmp_path / "suspicious.py").write_text("x")

    def _always_escapes(clone_root: Path, candidate: Path) -> Path:
        raise PathEscapesCloneRootError("forced for test")

    monkeypatch.setattr(file_ingestion_module, "resolve_within_clone_root", _always_escapes)

    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(
        tmp_path, max_file_size_bytes=1000, budget=budget, thread_pool_size=_POOL_SIZE
    )

    assert summary.stored == []
    assert len(summary.skipped) == 1
    assert summary.skipped[0].skip_reason == SkipReason.UNSAFE_PATH


def test_ingest_clone_tree_handles_hundreds_of_files_correctly(tmp_path: Path):
    for i in range(500):
        (tmp_path / f"file{i}.py").write_text(f"print({i})")

    budget = IngestBudget(max_file_count=10_000, max_total_bytes=100_000_000)
    summary = ingest_clone_tree(
        tmp_path, max_file_size_bytes=1000, budget=budget, thread_pool_size=8
    )

    assert len(summary.stored) == 500
    assert summary.skipped == []
    assert {f.relative_path for f in summary.stored} == {f"file{i}.py" for i in range(500)}
