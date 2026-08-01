"""Tests for the XSS heuristic."""

from vibeguard.core.heuristics.xss import find_xss_hits
from vibeguard.core.vuln_category import VulnCategory


def test_find_xss_hits_flags_dangerously_set_inner_html_true_positive():
    content = "<div dangerouslySetInnerHTML={{__html: userContent}} />"
    hits = find_xss_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.XSS


def test_find_xss_hits_flags_inner_html_assignment_true_positive():
    content = "el.innerHTML = userContent;"
    hits = find_xss_hits(content)
    assert len(hits) == 1


def test_find_xss_hits_flags_jinja_safe_filter_true_positive():
    content = "{{ user_bio | safe }}"
    hits = find_xss_hits(content)
    assert len(hits) == 1


def test_find_xss_hits_ignores_text_content_assignment_true_negative():
    content = "el.textContent = userContent;"
    assert find_xss_hits(content) == []


def test_find_xss_hits_ignores_plain_template_variable_true_negative():
    content = "{{ user_bio }}"
    assert find_xss_hits(content) == []
