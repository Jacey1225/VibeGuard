"""Tests for the SQL injection heuristic."""

from vibeguard.core.heuristics.injection import find_injection_hits
from vibeguard.core.vuln_category import VulnCategory


def test_find_injection_hits_flags_fstring_query_true_positive():
    content = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    hits = find_injection_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.INJECTION
    assert hits[0].line_number == 1


def test_find_injection_hits_flags_concatenated_query_true_positive():
    content = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    hits = find_injection_hits(content)
    assert len(hits) == 1


def test_find_injection_hits_ignores_parameterized_query_true_negative():
    content = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
    assert find_injection_hits(content) == []


def test_find_injection_hits_ignores_unrelated_fstring_true_negative():
    content = 'logger.info(f"Processing user {user_id}")'
    assert find_injection_hits(content) == []


def test_find_injection_hits_reports_correct_line_number():
    content = "\n".join(
        ["x = 1", 'cursor.execute(f"SELECT * FROM t WHERE id = {x}")', "y = 2"]
    )
    hits = find_injection_hits(content)
    assert hits[0].line_number == 2
