"""Password hashing and opaque token helpers.

Passwords use Argon2id. Session and reset tokens are random 256-bit values; only their SHA-256
digest is stored, so a database leak does not reveal usable tokens.
"""

import hashlib
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Verified against when an email is unknown, so failed logins take the same time either way.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def utcnow() -> datetime:
    return datetime.now(UTC)
