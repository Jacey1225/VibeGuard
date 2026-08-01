"""Remediation guidance for security misconfiguration."""

GUIDANCE = (
    "Disable debug mode in anything that could run in production "
    "(`DEBUG = False`, or read it from an environment variable defaulting "
    "to off) -- debug mode can leak stack traces, source code, and "
    "internal configuration to end users. Replace a wildcard CORS origin "
    "(`*`) with an explicit allowlist of trusted origins, especially "
    "anywhere credentials are also allowed -- the combination of "
    "wildcard origin and allowed credentials is equivalent to disabling "
    "CORS protection entirely. Replace any default or example credential "
    "literal with a value read from configuration, and never leave a "
    "real-looking placeholder in source."
)
