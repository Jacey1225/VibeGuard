"""Tests for decoding raw file bytes into storable text."""

from vibeguard.core.text_decode import decode_file_text


def test_decode_file_text_passes_through_valid_utf8():
    assert decode_file_text("hello 👋".encode()) == "hello 👋"


def test_decode_file_text_replaces_invalid_byte_sequences():
    raw = b"valid text \xff\xfe more text"
    decoded = decode_file_text(raw)
    assert "valid text" in decoded
    assert "more text" in decoded
    assert "�" in decoded


def test_decode_file_text_empty_bytes_is_empty_string():
    assert decode_file_text(b"") == ""
