"""Tests for the shared scan-request body schema."""

import pytest
from pydantic import ValidationError

from vibeguard.api.scan_schemas import ScanRequest
from vibeguard.core.vuln_category import VulnCategory


def test_scan_request_defaults_to_no_filter():
    request = ScanRequest()
    assert request.categories is None
    assert request.selected_categories() is None


def test_scan_request_with_categories_returns_a_frozenset():
    request = ScanRequest(categories=[VulnCategory.INJECTION, VulnCategory.XSS])
    assert request.selected_categories() == frozenset({VulnCategory.INJECTION, VulnCategory.XSS})


def test_scan_request_rejects_explicit_empty_list():
    with pytest.raises(ValidationError):
        ScanRequest(categories=[])


def test_scan_request_rejects_invalid_category_value():
    with pytest.raises(ValidationError):
        ScanRequest(categories=["not_a_real_category"])
