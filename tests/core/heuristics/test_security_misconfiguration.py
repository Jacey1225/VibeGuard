"""Tests for the security-misconfiguration heuristic."""

from vibeguard.core.heuristics.security_misconfiguration import (
    find_security_misconfiguration_hits,
)
from vibeguard.core.vuln_category import VulnCategory


def test_find_security_misconfiguration_hits_flags_debug_true_true_positive():
    content = "DEBUG = True"
    hits = find_security_misconfiguration_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.SECURITY_MISCONFIGURATION


def test_find_security_misconfiguration_hits_ignores_debug_false_true_negative():
    content = "DEBUG = False"
    assert find_security_misconfiguration_hits(content) == []


def test_find_security_misconfiguration_hits_flags_wildcard_cors_true_positive():
    content = 'app.add_middleware(CORSMiddleware, allow_origins=["*"])'
    hits = find_security_misconfiguration_hits(content)
    assert len(hits) == 1


def test_find_security_misconfiguration_hits_ignores_scoped_cors_true_negative():
    content = 'app.add_middleware(CORSMiddleware, allow_origins=["https://example.com"])'
    assert find_security_misconfiguration_hits(content) == []


def test_find_security_misconfiguration_hits_flags_default_credentials_true_positive():
    content = 'password = "admin"'
    hits = find_security_misconfiguration_hits(content)
    assert len(hits) == 1


def test_find_security_misconfiguration_hits_ignores_env_sourced_password_true_negative():
    content = "password = os.environ['DB_PASSWORD']"
    assert find_security_misconfiguration_hits(content) == []
