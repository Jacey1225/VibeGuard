"""The 10 OWASP-aligned vulnerability categories VibeGuard scans for.

Matches the checklist in `.claude/skills/vuln-scan/SKILL.md` exactly —
that skill is the spec this enum is a machine-readable mirror of.
"""

from enum import StrEnum


class VulnCategory(StrEnum):
    """One of the 10 vulnerability categories a finding belongs to."""

    INJECTION = "injection"
    BROKEN_AUTH = "broken_auth"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    CRYPTO_FAILURES = "crypto_failures"
    XXE_INSECURE_DESERIALIZATION = "xxe_insecure_deserialization"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    XSS = "xss"
    SSRF = "ssrf"
    VULNERABLE_DEPENDENCIES = "vulnerable_dependencies"
    INSUFFICIENT_LOGGING = "insufficient_logging"
