"""Simple, dependency-free auth (stdlib only).

Deliberately lightweight per the project's install-free constraint: password
hashing via ``hashlib.pbkdf2_hmac`` and opaque bearer tokens persisted in
SQLite. No JWT / passlib / python-jose.

Auth here is OPTIONAL and NON-BLOCKING. The existing public endpoints (/map,
/sessions, /ingest, /brands ...) do not require it, so the product keeps working
with no login UI. Tokens only gate /admin/* — and only when KUMU_ADMIN_AUTH is
turned on (default off => admin stays open exactly as before).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 120_000


def hash_password(password: str) -> str:
    """Return a self-describing hash string: algo$iters$salt_hex$hash_hex."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    )
    return f"{_ALGO}${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify against a stored hash produced by hash_password."""
    try:
        algo, iters, salt, hexhash = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iters)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(dk.hex(), hexhash)


def new_token() -> str:
    """A URL-safe opaque bearer token (stored server-side, not a JWT)."""
    return secrets.token_urlsafe(32)


def bearer_token(authorization: str | None) -> str | None:
    """Extract the token from an ``Authorization: Bearer <token>`` header."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return None
