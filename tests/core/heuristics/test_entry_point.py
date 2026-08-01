"""Tests for the Tier-B entry-point heuristic."""

from vibeguard.core.heuristics.entry_point import find_entry_point_hits
from vibeguard.core.vuln_category import VulnCategory


def test_find_entry_point_hits_flags_route_decorator_true_positive():
    content = '@app.post("/login")\ndef login(request):\n    pass'
    hits = find_entry_point_hits(content)
    assert len(hits) == 3
    assert {hit.category for hit in hits} == {
        VulnCategory.BROKEN_AUTH,
        VulnCategory.BROKEN_ACCESS_CONTROL,
        VulnCategory.INSUFFICIENT_LOGGING,
    }


def test_find_entry_point_hits_flags_login_function_true_positive():
    content = "def authenticate(username, password):\n    pass"
    hits = find_entry_point_hits(content)
    assert len(hits) == 3


def test_find_entry_point_hits_flags_exception_handler_true_positive():
    content = "try:\n    do_work()\nexcept ValueError:\n    pass"
    hits = find_entry_point_hits(content)
    assert len(hits) == 3


def test_find_entry_point_hits_ignores_plain_utility_function_true_negative():
    content = "def calculate_total(items):\n    return sum(items)"
    assert find_entry_point_hits(content) == []


def test_find_entry_point_hits_returns_only_the_first_match():
    content = "\n".join(
        [
            '@app.get("/a")',
            "def handler_a(): pass",
            '@app.get("/b")',
            "def handler_b(): pass",
        ]
    )
    hits = find_entry_point_hits(content)
    assert len(hits) == 3
    assert all(hit.line_number == 1 for hit in hits)
