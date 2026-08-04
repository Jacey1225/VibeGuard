"""Tests for narrowing a heuristic result down to selected categories."""

from vibeguard.core.heuristics.category_filter import filter_to_categories
from vibeguard.core.heuristics.run_heuristics import run_heuristics
from vibeguard.core.vuln_category import VulnCategory

_MULTI_CATEGORY_CONTENT = "\n".join(
    [
        'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
        'API_KEY = "sk_live_abcdef1234567890"',
    ]
)


def test_filter_to_categories_with_none_returns_result_unchanged():
    result = run_heuristics("multi.py", _MULTI_CATEGORY_CONTENT)
    assert result is not None

    filtered = filter_to_categories(result, None)

    assert filtered is result


def test_filter_to_categories_narrows_to_selected_subset():
    result = run_heuristics("multi.py", _MULTI_CATEGORY_CONTENT)
    assert result is not None
    assert set(result.categories) == {VulnCategory.INJECTION, VulnCategory.CRYPTO_FAILURES}

    filtered = filter_to_categories(result, frozenset({VulnCategory.INJECTION}))

    assert filtered is not None
    assert filtered.categories == (VulnCategory.INJECTION,)
    assert len(filtered.hits) == 1
    assert all(hit.category == VulnCategory.INJECTION for hit in filtered.hits)
    assert filtered.relative_path == "multi.py"


def test_filter_to_categories_excluding_every_matched_category_returns_none():
    result = run_heuristics("multi.py", _MULTI_CATEGORY_CONTENT)
    assert result is not None

    filtered = filter_to_categories(result, frozenset({VulnCategory.SSRF}))

    assert filtered is None


def test_filter_to_categories_with_all_matched_categories_selected_keeps_everything():
    result = run_heuristics("multi.py", _MULTI_CATEGORY_CONTENT)
    assert result is not None

    filtered = filter_to_categories(
        result, frozenset({VulnCategory.INJECTION, VulnCategory.CRYPTO_FAILURES})
    )

    assert filtered is not None
    assert set(filtered.categories) == {VulnCategory.INJECTION, VulnCategory.CRYPTO_FAILURES}
    assert len(filtered.hits) == 2


def test_filter_to_categories_narrows_a_combined_entry_point_match_to_one_category():
    # find_entry_point_hits tags a single matched line with all three
    # Tier-B categories at once (broken_auth/broken_access_control/
    # insufficient_logging) -- selecting just one of those three must
    # narrow the combined hit down to that category alone, not drop the
    # whole file.
    content = "@app.route('/admin')\ndef admin_panel():\n    return 'ok'"
    result = run_heuristics("app.py", content)
    assert result is not None
    assert set(result.categories) == {
        VulnCategory.BROKEN_AUTH,
        VulnCategory.BROKEN_ACCESS_CONTROL,
        VulnCategory.INSUFFICIENT_LOGGING,
    }

    filtered = filter_to_categories(result, frozenset({VulnCategory.BROKEN_ACCESS_CONTROL}))

    assert filtered is not None
    assert filtered.categories == (VulnCategory.BROKEN_ACCESS_CONTROL,)
    assert len(filtered.hits) == 1
