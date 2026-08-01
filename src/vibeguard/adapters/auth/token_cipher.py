"""Encrypting/decrypting GitHub OAuth tokens at rest via Fernet.

Fernet (AES-128-CBC + HMAC, via the `cryptography` package) rather than
raw AES-GCM: Fernet handles nonce/IV generation internally, avoiding
the manual-nonce-management footgun where reuse is catastrophic —
exactly the mistake to avoid on this codebase's first crypto
integration. Ciphertext is URL-safe base64 text, so it fits the
existing `Text` column convention directly.
"""

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr


class TokenDecryptionError(RuntimeError):
    """Raised when a stored ciphertext can't be decrypted with the configured key."""


def encrypt_token(raw_token: str, encryption_key: SecretStr) -> str:
    """Encrypt a raw GitHub access token for storage."""
    fernet = Fernet(encryption_key.get_secret_value().encode())
    return fernet.encrypt(raw_token.encode()).decode()


def decrypt_token(ciphertext: str, encryption_key: SecretStr) -> str:
    """Decrypt a stored ciphertext back into the raw GitHub access token.

    Raises:
        TokenDecryptionError: the ciphertext doesn't decrypt with the
            configured key (wrong key, corrupted data, or tampering).
    """
    fernet = Fernet(encryption_key.get_secret_value().encode())
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as error:
        raise TokenDecryptionError("stored token ciphertext could not be decrypted") from error
