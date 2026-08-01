"""Remediation guidance for server-side request forgery."""

GUIDANCE = (
    "Never build an outbound request's URL or host directly from "
    "user-controlled input via string interpolation or concatenation. If "
    "the feature genuinely needs to fetch a user-supplied URL, validate "
    "the resolved host against an explicit allowlist before making the "
    "request, and reject internal/private IP ranges and non-http(s) "
    "schemes. If the destination is meant to be one of a known, fixed "
    "set of hosts, replace the dynamic URL construction with a lookup "
    "into that fixed set instead."
)
