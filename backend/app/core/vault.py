"""Encryption for interview-source credentials.

Secrets are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) under keys that come from the
environment only (IPP_CREDENTIALS_KEYS), never from code or the database. Several keys can be
configured, newest first: decryption tries each one and encryption always uses the newest, so a key
can be rotated without downtime (see `python -m app.cli rotate-credentials`).
"""

import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.core.config import get_settings


class VaultError(RuntimeError):
    pass


def parse_keys(raw: str) -> list[str]:
    return [key.strip() for key in raw.split(",") if key.strip()]


def key_id(key: str) -> str:
    """A short, non-reversible fingerprint that says which key encrypted a row."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


class CredentialVault:
    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise VaultError("No credential encryption key is configured.")
        try:
            fernets = [Fernet(key.encode()) for key in keys]
        except (ValueError, TypeError):
            raise VaultError(
                "IPP_CREDENTIALS_KEYS contains an invalid key. Generate one with "
                "`python -m app.cli generate-credentials-key`."
            ) from None
        self._fernet = MultiFernet(fernets)
        self.current_key_id = key_id(keys[0])

    def encrypt(self, values: dict[str, str]) -> str:
        return self._fernet.encrypt(json.dumps(values).encode()).decode()

    def decrypt(self, token: str) -> dict[str, str]:
        try:
            return json.loads(self._fernet.decrypt(token.encode()))
        except InvalidToken:
            raise VaultError(
                "Stored credentials could not be decrypted. The key that encrypted them may have "
                "been removed from IPP_CREDENTIALS_KEYS; enter the credentials again."
            ) from None

    def rotate(self, token: str) -> str:
        """Re-encrypt under the newest key."""
        try:
            return self._fernet.rotate(token.encode()).decode()
        except InvalidToken:
            raise VaultError("A stored credential could not be decrypted with any key.") from None


def get_vault() -> CredentialVault | None:
    """The configured vault, or None when no key is set (credentials cannot be stored then)."""
    configured = get_settings().credentials_keys
    if configured is None:
        return None
    return CredentialVault(parse_keys(configured.get_secret_value()))
