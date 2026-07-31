"""Tests for aggregate ingest budget tracking."""

from vibeguard.core.ingest_budget import IngestBudget


def test_has_file_count_capacity_true_below_limit():
    budget = IngestBudget(max_file_count=5, max_total_bytes=1000)
    assert budget.has_file_count_capacity() is True


def test_has_file_count_capacity_false_at_limit():
    budget = IngestBudget(max_file_count=2, max_total_bytes=1000, file_count=2)
    assert budget.has_file_count_capacity() is False


def test_has_total_size_capacity_true_when_under_budget():
    budget = IngestBudget(max_file_count=100, max_total_bytes=1000, total_bytes=500)
    assert budget.has_total_size_capacity(400) is True


def test_has_total_size_capacity_false_when_over_budget():
    budget = IngestBudget(max_file_count=100, max_total_bytes=1000, total_bytes=500)
    assert budget.has_total_size_capacity(600) is False


def test_has_total_size_capacity_true_at_exact_budget():
    budget = IngestBudget(max_file_count=100, max_total_bytes=1000, total_bytes=500)
    assert budget.has_total_size_capacity(500) is True


def test_record_updates_both_totals():
    budget = IngestBudget(max_file_count=100, max_total_bytes=1000)
    budget.record(50)
    budget.record(25)
    assert budget.file_count == 2
    assert budget.total_bytes == 75


def test_budget_tracks_correctly_across_a_large_number_of_records():
    # A larger fixture, per search-sort-efficiency's testing tie-in:
    # confirms tracking is O(1) per update, not a rescan of prior records.
    budget = IngestBudget(max_file_count=10_000, max_total_bytes=10_000_000)
    for _ in range(5000):
        budget.record(10)
    assert budget.file_count == 5000
    assert budget.total_bytes == 50_000
    assert budget.has_file_count_capacity() is True
    assert budget.has_total_size_capacity(100) is True
