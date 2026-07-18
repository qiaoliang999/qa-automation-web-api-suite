"""Password hashing and token helpers for TaskTrack."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone


# pbkdf2_sha256 — stdlib only, no native bcrypt dependency in CI.
# 120k is fine for production-like demos; tests may lower via TASKTRACK_PBKDF2_ITERATIONS.
_HASH_ALGO = "sha256"
_DEFAULT_ITERATIONS = 120_000
_SALT_BYTES = 16


def _iterations() -> int:
    raw = os.getenv("TASKTRACK_PBKDF2_ITERATIONS")
    if raw:
        return max(1_000, int(raw))
    return _DEFAULT_ITERATIONS


def hash_password(password: str, *, iterations: int | None = None) -> str:
    """Return a portable `pbkdf2$iterations$salt$hash` string."""
    iters = iterations if iterations is not None else _iterations()
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        _HASH_ALGO,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iters,
    ).hex()
    return f"pbkdf2_{_HASH_ALGO}${iters}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        scheme, iterations_s, salt, expected = password_hash.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        algo = scheme.removeprefix("pbkdf2_")
        iterations = int(iterations_s)
    except (ValueError, AttributeError):
        return False

    digest = hashlib.pbkdf2_hmac(
        algo,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(digest, expected)


def generate_token() -> str:
    """Opaque random session token (not a JWT — documented residual risk)."""
    return secrets.token_urlsafe(32)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
