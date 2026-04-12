from __future__ import annotations

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2.low_level import Type, hash_secret_raw
from monero.seed import Seed


def normalize_mnemonic(phrase: str) -> str:
    """Collapse whitespace; Monero mnemonics are conventionally lowercase."""
    return " ".join(phrase.strip().lower().split())


def generate_mnemonic_phrase() -> str:
    """Return a new random 25-word Monero-standard mnemonic (never log this)."""
    return Seed().phrase


def mnemonic_to_seed_hex(phrase: str) -> str:
    """Parse mnemonic; raises ValueError if invalid."""
    normalized = normalize_mnemonic(phrase)
    if not normalized:
        raise ValueError("mnemonic is empty")
    try:
        return Seed(normalized).hex_seed()
    except Exception as exc:  # noqa: BLE001 — library raises varied errors
        raise ValueError("invalid Monero mnemonic") from exc


def derive_user_id(seed_hex: str) -> str:
    """
    Deterministic opaque account id from the wallet seed bytes.
    The server never stores the mnemonic or raw seed hex; only this id and session tokens.
    """
    raw = bytes.fromhex(seed_hex)
    return hashlib.sha256(raw).hexdigest()


def hash_mnemonic_for_pending(normalized_mnemonic: str, pepper: bytes) -> str:
    """
    Argon2id digest (hex) for short-lived pending registration rows.
    `pepper` binds the digest to this setup_token (server secret + token).
    """
    salt = os.urandom(16)
    secret = pepper + normalized_mnemonic.encode("utf-8")
    digest = hash_secret_raw(
        secret=secret,
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )
    return salt.hex() + ":" + digest.hex()


def verify_mnemonic_pending(normalized_mnemonic: str, stored: str, pepper: bytes) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    secret = pepper + normalized_mnemonic.encode("utf-8")
    candidate = hash_secret_raw(
        secret=secret,
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=2,
        hash_len=len(expected),
        type=Type.ID,
    )
    return hmac.compare_digest(candidate, expected)


def jwt_secret() -> bytes:
    raw = os.getenv("ROBOSATS_XMR_JWT_SECRET", "")
    if not raw:
        return b"dev-only-change-ROBOSATS_XMR_JWT_SECRET"
    return raw.encode("utf-8")


def issue_access_token(*, user_id: str, ttl_hours: int = 168) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl_hours)).timestamp()),
        "typ": "access",
    }
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return str(sub) if isinstance(sub, str) and sub else None


def pepper_for_pending(setup_token: str, server_secret: bytes) -> bytes:
    return hmac.new(server_secret, setup_token.encode("utf-8"), hashlib.sha256).digest()


def registration_server_secret() -> bytes:
    raw = os.getenv("ROBOSATS_XMR_REGISTRATION_SECRET", "")
    if not raw:
        return b"dev-only-change-ROBOSATS_XMR_REGISTRATION_SECRET"
    return raw.encode("utf-8")
