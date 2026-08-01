"""Assembling category-specific remediation guidance for the LLM prompt."""

from collections.abc import Iterable

from vibeguard.core.remediation_guidance import (
    broken_access_control,
    broken_auth,
    crypto_failures,
    injection,
    insufficient_logging,
    security_misconfiguration,
    ssrf,
    vulnerable_dependencies,
    xss,
    xxe_insecure_deserialization,
)
from vibeguard.core.vuln_category import VulnCategory

_GUIDANCE_BY_CATEGORY: dict[VulnCategory, str] = {
    VulnCategory.INJECTION: injection.GUIDANCE,
    VulnCategory.BROKEN_AUTH: broken_auth.GUIDANCE,
    VulnCategory.BROKEN_ACCESS_CONTROL: broken_access_control.GUIDANCE,
    VulnCategory.CRYPTO_FAILURES: crypto_failures.GUIDANCE,
    VulnCategory.XXE_INSECURE_DESERIALIZATION: xxe_insecure_deserialization.GUIDANCE,
    VulnCategory.SECURITY_MISCONFIGURATION: security_misconfiguration.GUIDANCE,
    VulnCategory.XSS: xss.GUIDANCE,
    VulnCategory.SSRF: ssrf.GUIDANCE,
    VulnCategory.VULNERABLE_DEPENDENCIES: vulnerable_dependencies.GUIDANCE,
    VulnCategory.INSUFFICIENT_LOGGING: insufficient_logging.GUIDANCE,
}


def assemble_guidance_section(categories: Iterable[VulnCategory]) -> str:
    """Build the guidance block for a prompt, covering exactly the given categories.

    Iterates in `VulnCategory`'s own declared order, not the input's
    order, so the assembled prompt text is deterministic regardless of
    finding order.
    """
    requested = set(categories)
    sections = [
        f"- {category.value}: {_GUIDANCE_BY_CATEGORY[category]}"
        for category in VulnCategory
        if category in requested
    ]
    return "\n".join(sections)
