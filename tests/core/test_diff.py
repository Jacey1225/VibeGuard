"""Tests for unified diff computation."""

from vibeguard.core.diff import compute_unified_diff


def test_compute_unified_diff_shows_changed_lines():
    original = "line1\nline2\nline3\n"
    proposed = "line1\nCHANGED\nline3\n"

    diff = compute_unified_diff(original, proposed, "app.py")

    assert "-line2" in diff
    assert "+CHANGED" in diff
    assert "a/app.py" in diff
    assert "b/app.py" in diff


def test_compute_unified_diff_identical_content_is_empty():
    content = "unchanged\n"
    assert compute_unified_diff(content, content, "app.py") == ""
