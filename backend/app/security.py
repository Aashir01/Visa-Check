"""Password hashing, JWT issuance, and at-rest file encryption."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from .config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_ALGO = "HS256"


def hash_password(raw: str) -> str:
    # bcrypt silently truncates at 72 bytes; pre-hash so long passphrases keep
    # their full entropy.
    return _pwd.hash(_prehash(raw))


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _pwd.verify(_prehash(raw), hashed)
    except ValueError:
        return False


def _prehash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGO)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None


# --- at-rest encryption for uploaded passports / bank statements (§9) ---

_fernet = Fernet(settings.fernet_key)


def encrypt_bytes(raw: bytes) -> bytes:
    return _fernet.encrypt(raw)


def decrypt_bytes(blob: bytes) -> bytes:
    try:
        return _fernet.decrypt(blob)
    except InvalidToken as exc:
        raise ValueError(
            "Stored file could not be decrypted — SECRET_KEY may have changed."
        ) from exc
