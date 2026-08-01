"""Tests for the heuristic orchestrator's dedup-to-one-result-per-file property."""

from vibeguard.core.heuristics.run_heuristics import run_heuristics
from vibeguard.core.vuln_category import VulnCategory


def test_run_heuristics_returns_none_for_clean_file():
    content = "def calculate_total(items):\n    return sum(items)"
    assert run_heuristics("clean.py", content) is None


def test_run_heuristics_returns_result_for_single_category_match():
    content = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    result = run_heuristics("query.py", content)
    assert result is not None
    assert result.relative_path == "query.py"
    assert result.categories == (VulnCategory.INJECTION,)
    assert len(result.hits) == 1


def test_run_heuristics_dedupes_multi_category_file_to_one_result():
    # A file matching both the injection heuristic and a Tier-A crypto
    # heuristic should still be exactly one HeuristicScanResult, with
    # both categories listed -- not two separate results.
    content = "\n".join(
        [
            'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
            'API_KEY = "sk_live_abcdef1234567890"',
        ]
    )
    result = run_heuristics("multi.py", content)
    assert result is not None
    assert set(result.categories) == {VulnCategory.INJECTION, VulnCategory.CRYPTO_FAILURES}
    assert len(result.hits) == 2


def test_run_heuristics_dedupes_repeated_category_hits_to_one_category_entry():
    content = "\n".join(
        [
            'cursor.execute(f"SELECT * FROM a WHERE id = {x}")',
            'cursor.execute(f"SELECT * FROM b WHERE id = {y}")',
        ]
    )
    result = run_heuristics("repeated.py", content)
    assert result is not None
    assert result.categories == (VulnCategory.INJECTION,)
    assert len(result.hits) == 2


def test_run_heuristics_across_a_large_number_of_files_only_flags_matching_ones():
    # Per search-sort-efficiency's testing tie-in: a larger fixture,
    # not just a 2-3 file happy path.
    clean_results = [
        run_heuristics(f"clean{i}.py", f"def f{i}(x):\n    return x + {i}") for i in range(300)
    ]
    flagged_results = [
        run_heuristics(f"flagged{i}.py", 'password = "admin"') for i in range(50)
    ]

    assert all(result is None for result in clean_results)
    assert all(result is not None for result in flagged_results)
    assert all(
        result.categories == (VulnCategory.SECURITY_MISCONFIGURATION,)
        for result in flagged_results
        if result is not None
    )
