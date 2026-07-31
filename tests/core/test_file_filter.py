"""Tests for per-file size/binary classification."""

from vibeguard.core.file_filter import exceeds_max_file_size, looks_binary


def test_exceeds_max_file_size_below_limit_returns_false():
    assert exceeds_max_file_size(size_bytes=99, max_bytes=100) is False


def test_exceeds_max_file_size_at_limit_returns_false():
    assert exceeds_max_file_size(size_bytes=100, max_bytes=100) is False


def test_exceeds_max_file_size_over_limit_returns_true():
    assert exceeds_max_file_size(size_bytes=101, max_bytes=100) is True


def test_looks_binary_detects_nul_byte():
    assert looks_binary(b"hello\x00world") is True


def test_looks_binary_plain_text_is_not_binary():
    assert looks_binary(b"def main():\n    pass\n") is False


def test_looks_binary_empty_sample_is_not_binary():
    assert looks_binary(b"") is False


def test_looks_binary_only_checks_the_sniff_window():
    # A NUL byte far past the sniff window shouldn't trigger a false
    # positive on an otherwise-text sample truncated to that window.
    sample = (b"a" * 8000) + b"\x00"
    assert looks_binary(sample[:8000]) is False
