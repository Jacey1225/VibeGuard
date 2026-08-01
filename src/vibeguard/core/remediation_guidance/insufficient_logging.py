"""Remediation guidance for insufficient logging and monitoring."""

GUIDANCE = (
    "Add a log statement at the point authentication, authorization, or "
    "input validation fails, including enough context to investigate "
    "later (which check failed, an identifier for the actor/request) -- "
    "but never log the credential, token, or secret value itself, even "
    "at debug level, and never log full request/response bodies that "
    "might contain sensitive data. If sensitive data is currently being "
    "logged, replace it with a redacted or reference form (e.g. the last "
    "4 characters, or an internal id) rather than removing the log line "
    "entirely."
)
