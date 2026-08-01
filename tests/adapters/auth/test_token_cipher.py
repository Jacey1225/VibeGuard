"""Tests for GitHub OAuth token encryption at rest."""

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from vibeguard.adapters.auth.token_cipher import TokenDecryptionError, decrypt_token, encrypt_token

_KEY = SecretStr(Fernet.generate_key().decode())


def test_encrypt_then_decrypt_round_trips():
    ciphertext = encrypt_token("gho_realtoken123", _KEY)
    assert decrypt_token(ciphertext, _KEY) == "gho_realtoken123"


def test_ciphertext_does_not_contain_the_plaintext():
    ciphertext = encrypt_token("gho_realtoken123", _KEY)
    assert "gho_realtoken123" not in ciphertext


def test_ciphertext_differs_per_call_for_identical_plaintext():
    # Guards against a future accidental switch to a deterministic mode
    # -- Fernet's built-in IV should make each encryption unique.
    first = encrypt_token("same-token", _KEY)
    second = encrypt_token("same-token", _KEY)
    assert first != second


def test_decrypt_with_wrong_key_raises():
    ciphertext = encrypt_token("gho_realtoken123", _KEY)
    wrong_key = SecretStr(Fernet.generate_key().decode())
    with pytest.raises(TokenDecryptionError):
        decrypt_token(ciphertext, wrong_key)


def test_decrypt_tampered_ciphertext_raises():
    ciphertext = encrypt_token("gho_realtoken123", _KEY)
    tampered = ciphertext[:-4] + ("A" * 4)
    with pytest.raises(TokenDecryptionError):
        decrypt_token(tampered, _KEY)
