"""Remediation guidance for broken authentication and session management."""

GUIDANCE = (
    "Store passwords hashed with a slow, salted algorithm (bcrypt, argon2, "
    "or scrypt) -- never plaintext, MD5, or SHA1. Generate session tokens "
    "with a cryptographically secure random source (e.g. Python's "
    "`secrets` module), never a predictable value (sequential ids, "
    "timestamps, weak PRNGs). Never place a session token or credential "
    "in a URL (query string or path) -- it belongs in a header, cookie, "
    "or request body. If the finding concerns missing authentication on "
    "an entry point, add an explicit check rather than relying on the "
    "caller to have already authenticated."
)
