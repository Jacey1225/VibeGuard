"""Tests for bounded file reads."""

from pathlib import Path

import pytest

from vibeguard.adapters.filesystem.file_read import (
    read_file_contents,
    read_file_sample,
    read_file_size,
)


def test_read_file_size_returns_byte_count(tmp_path: Path):
    path = tmp_path / "f.txt"
    path.write_bytes(b"12345")
    assert read_file_size(path) == 5


def test_read_file_sample_reads_only_the_sniff_window(tmp_path: Path):
    path = tmp_path / "big.bin"
    path.write_bytes(b"a" * 20000)
    sample = read_file_sample(path)
    assert len(sample) == 8000


def test_read_file_sample_shorter_than_window_reads_whole_file(tmp_path: Path):
    path = tmp_path / "small.txt"
    path.write_bytes(b"short")
    assert read_file_sample(path) == b"short"


def test_read_file_contents_reads_full_contents_within_bound(tmp_path: Path):
    path = tmp_path / "f.txt"
    path.write_bytes(b"hello")
    assert read_file_contents(path, max_bytes=100) == b"hello"


def test_read_file_contents_raises_when_actual_content_exceeds_bound(tmp_path: Path):
    path = tmp_path / "f.txt"
    path.write_bytes(b"x" * 200)
    with pytest.raises(ValueError):
        read_file_contents(path, max_bytes=100)
