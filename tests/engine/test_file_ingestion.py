"""Tests for walking, filtering, and reading a cloned repository's files."""

from pathlib import Path

from vibeguard.core.file_filter import SkippedFile, StoredFile
from vibeguard.core.ingest_budget import IngestBudget
from vibeguard.core.repository_status import SkipReason
from vibeguard.engine.file_ingestion import ingest_clone_tree, ingest_single_file


def test_ingest_single_file_stores_small_text_file(tmp_path: Path):
    path = tmp_path / "a.py"
    path.write_text("print(1)")
    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)

    outcome = ingest_single_file(path, "a.py", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, StoredFile)
    assert outcome.content == "print(1)"
    assert budget.file_count == 1


def test_ingest_single_file_skips_oversized_file(tmp_path: Path):
    path = tmp_path / "big.py"
    path.write_bytes(b"x" * 2000)
    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)

    outcome = ingest_single_file(path, "big.py", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.TOO_LARGE
    assert budget.file_count == 0


def test_ingest_single_file_skips_binary_file(tmp_path: Path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01\x02binary")
    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)

    outcome = ingest_single_file(path, "data.bin", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.BINARY


def test_ingest_single_file_skips_when_file_count_budget_exhausted(tmp_path: Path):
    path = tmp_path / "a.py"
    path.write_text("x")
    budget = IngestBudget(max_file_count=1, max_total_bytes=1_000_000, file_count=1)

    outcome = ingest_single_file(path, "a.py", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.FILE_COUNT_LIMIT_EXCEEDED


def test_ingest_single_file_skips_when_content_read_exceeds_bound_toctou(
    tmp_path: Path, monkeypatch
):
    # Simulates a file that grew between the size check and the read
    # (TOCTOU): read_file_contents' defensive bound still catches it.
    path = tmp_path / "a.py"
    path.write_text("x")
    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)

    import vibeguard.engine.file_ingestion as file_ingestion_module

    def _raise_value_error(path, max_bytes):
        raise ValueError("grew after the size check")

    monkeypatch.setattr(file_ingestion_module, "read_file_contents", _raise_value_error)

    outcome = ingest_single_file(path, "a.py", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.TOO_LARGE
    assert budget.file_count == 0


def test_ingest_single_file_skips_when_total_size_budget_exhausted(tmp_path: Path):
    path = tmp_path / "a.py"
    path.write_text("x" * 50)
    budget = IngestBudget(max_file_count=100, max_total_bytes=100, total_bytes=90)

    outcome = ingest_single_file(path, "a.py", max_file_size_bytes=1000, budget=budget)

    assert isinstance(outcome, SkippedFile)
    assert outcome.skip_reason == SkipReason.TOTAL_SIZE_LIMIT_EXCEEDED


def test_ingest_clone_tree_stores_and_skips_correctly(tmp_path: Path):
    (tmp_path / "keep.py").write_text("print('hi')")
    (tmp_path / "too_big.py").write_bytes(b"x" * 2000)
    (tmp_path / "binary.bin").write_bytes(b"\x00binary")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("should never be seen")

    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(tmp_path, max_file_size_bytes=1000, budget=budget)

    stored_paths = {f.relative_path for f in summary.stored}
    skipped_paths = {f.relative_path for f in summary.skipped}
    assert stored_paths == {"keep.py"}
    assert skipped_paths == {"too_big.py", "binary.bin"}
    assert summary.files_truncated is False


def test_ingest_clone_tree_marks_truncation_when_file_count_exceeded(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"file{i}.py").write_text("x")

    budget = IngestBudget(max_file_count=2, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(tmp_path, max_file_size_bytes=1000, budget=budget)

    assert len(summary.stored) == 2
    assert len(summary.skipped) == 3
    assert summary.files_truncated is True
    assert summary.truncation_reason == SkipReason.FILE_COUNT_LIMIT_EXCEEDED.value


def test_ingest_clone_tree_records_path_escape_as_skipped_not_a_crash(tmp_path: Path, monkeypatch):
    # tree_walk already skips symlinked files outright, so the escape
    # guard in resolve_within_clone_root is a defense-in-depth backstop
    # that's hard to trigger through the walk itself -- exercise it
    # directly by forcing the guard to fire for this file.
    (tmp_path / "suspicious.py").write_text("x")

    import vibeguard.engine.file_ingestion as file_ingestion_module
    from vibeguard.adapters.filesystem.path_containment import PathEscapesCloneRootError

    def _always_escapes(clone_root, candidate):
        raise PathEscapesCloneRootError("forced for test")

    monkeypatch.setattr(file_ingestion_module, "resolve_within_clone_root", _always_escapes)

    budget = IngestBudget(max_file_count=100, max_total_bytes=1_000_000)
    summary = ingest_clone_tree(tmp_path, max_file_size_bytes=1000, budget=budget)

    assert summary.stored == []
    assert len(summary.skipped) == 1
    assert summary.skipped[0].skip_reason == SkipReason.UNSAFE_PATH
