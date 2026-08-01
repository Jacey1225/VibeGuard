"""Tests for the crypto-failures heuristic (hardcoded secrets, weak TLS/crypto)."""

from vibeguard.core.heuristics.crypto_failures import find_crypto_failures_hits
from vibeguard.core.vuln_category import VulnCategory


def test_find_crypto_failures_hits_flags_hardcoded_api_key_true_positive():
    content = 'API_KEY = "sk_live_abcdef1234567890"'
    hits = find_crypto_failures_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.CRYPTO_FAILURES


def test_find_crypto_failures_hits_ignores_env_var_lookup_true_negative():
    content = 'API_KEY = os.environ["API_KEY"]'
    assert find_crypto_failures_hits(content) == []


def test_find_crypto_failures_hits_ignores_getenv_true_negative():
    content = 'password = os.getenv("DB_PASSWORD")'
    assert find_crypto_failures_hits(content) == []


def test_find_crypto_failures_hits_flags_disabled_tls_verification_true_positive():
    content = "requests.get(url, verify=False)"
    hits = find_crypto_failures_hits(content)
    assert len(hits) == 1


def test_find_crypto_failures_hits_ignores_normal_request_true_negative():
    content = "requests.get(url, timeout=5)"
    assert find_crypto_failures_hits(content) == []


def test_find_crypto_failures_hits_flags_md5_true_positive():
    content = "digest = hashlib.md5(data).hexdigest()"
    hits = find_crypto_failures_hits(content)
    assert len(hits) == 1


def test_find_crypto_failures_hits_ignores_sha256_true_negative():
    content = "digest = hashlib.sha256(data).hexdigest()"
    assert find_crypto_failures_hits(content) == []
