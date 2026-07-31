"""Tests for the cheap pre-clone size circuit breaker."""

from vibeguard.core.precheck import exceeds_precheck_size_budget


def test_exceeds_precheck_size_budget_false_when_well_under_budget():
    result = exceeds_precheck_size_budget(size_kb=100, max_total_bytes=1_000_000, fudge_factor=1.5)
    assert result is False


def test_exceeds_precheck_size_budget_true_when_far_over_budget():
    result = exceeds_precheck_size_budget(
        size_kb=10_000_000, max_total_bytes=1_000_000, fudge_factor=1.5
    )
    assert result is True


def test_exceeds_precheck_size_budget_respects_fudge_factor():
    # Reported size is over the raw max but within the fudged allowance.
    max_total_bytes = 1000
    size_kb = 1  # 1024 bytes reported, just over max_total_bytes
    assert exceeds_precheck_size_budget(size_kb, max_total_bytes, fudge_factor=1.5) is False
    assert exceeds_precheck_size_budget(size_kb, max_total_bytes, fudge_factor=1.0) is True
