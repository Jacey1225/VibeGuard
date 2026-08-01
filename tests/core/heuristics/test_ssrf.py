"""Tests for the SSRF heuristic."""

from vibeguard.core.heuristics.ssrf import find_ssrf_hits
from vibeguard.core.vuln_category import VulnCategory


def test_find_ssrf_hits_flags_fstring_url_true_positive():
    content = 'requests.get(f"http://{host}/status")'
    hits = find_ssrf_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.SSRF


def test_find_ssrf_hits_flags_concatenated_url_true_positive():
    content = 'requests.get("http://" + host + "/status")'
    hits = find_ssrf_hits(content)
    assert len(hits) == 1


def test_find_ssrf_hits_ignores_static_url_true_negative():
    content = 'requests.get("https://api.example.com/status")'
    assert find_ssrf_hits(content) == []


def test_find_ssrf_hits_ignores_unrelated_fstring_true_negative():
    content = 'logger.info(f"fetching status for {host}")'
    assert find_ssrf_hits(content) == []
