"""Remediation guidance for broken access control."""

GUIDANCE = (
    "Add an explicit authorization check before performing the action -- "
    "verify the authenticated caller actually owns or has been granted "
    "access to the specific object being requested, not just that they "
    "are logged in (authentication is not authorization). Never trust an "
    "object id taken directly from user input (path, query, or body) "
    "without checking it against the caller's own records -- this is the "
    "IDOR pattern. For file access, resolve and validate that the final "
    "path stays within the intended directory before opening it, "
    "rejecting `../` traversal attempts rather than merely stripping "
    "them."
)
