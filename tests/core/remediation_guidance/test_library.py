"""Tests for the category-specific remediation guidance library."""

import pytest

from vibeguard.core.remediation_guidance.library import (
    _GUIDANCE_BY_CATEGORY,
    assemble_guidance_section,
)
from vibeguard.core.vuln_category import VulnCategory


@pytest.mark.parametrize("category", list(VulnCategory))
def test_every_category_has_a_guidance_entry(category: VulnCategory):
    # Catches a future 11th category shipping without guidance.
    assert category in _GUIDANCE_BY_CATEGORY
    assert len(_GUIDANCE_BY_CATEGORY[category]) > 0


def test_assemble_guidance_section_includes_only_requested_categories():
    section = assemble_guidance_section([VulnCategory.INJECTION])
    assert "injection" in section
    assert "xss" not in section


def test_assemble_guidance_section_is_deterministic_regardless_of_input_order():
    forward = assemble_guidance_section([VulnCategory.XSS, VulnCategory.INJECTION])
    backward = assemble_guidance_section([VulnCategory.INJECTION, VulnCategory.XSS])
    assert forward == backward


def test_assemble_guidance_section_orders_by_declared_enum_order():
    section = assemble_guidance_section([VulnCategory.XSS, VulnCategory.INJECTION])
    assert section.index("injection") < section.index("xss")


def test_assemble_guidance_section_empty_input_returns_empty_string():
    assert assemble_guidance_section([]) == ""
