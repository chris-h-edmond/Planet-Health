"""Password hashing, session token and CSRF token primitives.

* Passwords are hashed with Argon2id (argon2-cffi).
* Session and CSRF tokens are cryptographically random values.  Only their
  SHA-256 digests are persisted, so a database leak does not expose usable
  session credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Argon2id is the default type of argon2-cffi's PasswordHasher.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain-text password against an Argon2id hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # pragma: no cover - defensive, argon2 raises typed errors
        return False


def needs_rehash(password_hash: str) -> bool:
    """Return True when a stored hash should be upgraded to current parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:  # pragma: no cover - defensive
        return False


def generate_token(nbytes: int = 32) -> str:
    """Generate a URL-safe cryptographically random token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token (used for at-rest storage)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(candidate: str, expected_hash: str) -> bool:
    """Constant-time comparison of a raw token against a stored digest."""
    if not candidate:
        return False
    return hmac.compare_digest(hash_token(candidate), expected_hash)
