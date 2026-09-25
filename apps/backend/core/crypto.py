"""Encryption for credentials the product stores on someone's behalf.

A private calendar subscribe URL is not configuration, it is a bearer
credential: anyone holding it can read that person's calendar, indefinitely,
without them ever being told. Storing it as plain JSON would mean a
database dump, a debug log or an over-broad admin query hands out standing
access to employees' calendars - in the one product where that is least
acceptable.

Fernet (AES-128-CBC + HMAC) with a key derived from APP_SECRET_KEY. That
ties the ciphertext to the same secret everything else already depends on,
so there is one thing to protect rather than two. The cost is that rotating
APP_SECRET_KEY makes stored connector configs undecryptable - callers treat
that as "needs reconnecting" rather than crashing, and
docs/deployment.md says so.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from apps.backend.core.config import get_settings

logger = logging.getLogger("workwell.crypto")


class UndecryptableSecret(RuntimeError):
    """The stored value cannot be read with the current key."""


@lru_cache
def _fernet() -> Fernet:
    # A 32-byte key from the app secret. SHA-256 rather than a slow KDF on
    # purpose: this is a key-derivation from an already-high-entropy secret,
    # not password hashing, and it runs on every connector read.
    digest = hashlib.sha256(get_settings().app_secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_dict(payload: dict) -> str:
    return _fernet().encrypt(json.dumps(payload, sort_keys=True).encode()).decode()


def decrypt_dict(token: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(token.encode()).decode())
    except (InvalidToken, ValueError) as exc:
        # Almost always a rotated APP_SECRET_KEY. Never log the ciphertext.
        raise UndecryptableSecret(
            "stored secret cannot be decrypted with the current APP_SECRET_KEY"
        ) from exc


def redact(value: str, keep: int = 4) -> str:
    """For showing an employee which credential is stored without showing
    them - or anyone over their shoulder - the credential."""
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "…"
    return f"{value[:keep]}…{value[-keep:]}"
