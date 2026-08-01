"""Remediation guidance for cryptographic failures (secrets, weak crypto/TLS)."""

GUIDANCE = (
    "For a hardcoded secret (API key, password, token): replace the "
    "literal value with a read from an environment variable or a secrets "
    "manager, and explicitly state in your summary that the "
    "previously-hardcoded value is already exposed in the repository's "
    "git history and must be rotated at the source -- removing it from "
    "the file does not invalidate it. For disabled TLS verification: "
    "remove the override (e.g. `verify=False`, `CERT_NONE`) so the "
    "default, secure verification behavior applies; if a specific CA "
    "bundle is genuinely needed, pass it explicitly rather than disabling "
    "verification. For a weak algorithm (MD5, SHA1, DES, RC4): replace it "
    "with a current standard for the same purpose (SHA-256 or better for "
    "hashing/integrity, bcrypt/argon2/scrypt for password storage, AES "
    "for symmetric encryption)."
)
