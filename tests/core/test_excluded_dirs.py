"""Tests for excluded-directory membership checks."""

from vibeguard.core.excluded_dirs import is_excluded_directory


def test_is_excluded_directory_true_for_git():
    assert is_excluded_directory(".git") is True


def test_is_excluded_directory_true_for_node_modules():
    assert is_excluded_directory("node_modules") is True


def test_is_excluded_directory_false_for_ordinary_directory():
    assert is_excluded_directory("src") is False


def test_is_excluded_directory_is_case_sensitive():
    assert is_excluded_directory(".GIT") is False
