import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.config import settings


def _prehash(password: str) -> bytes:
    # SHA-256 pre-hash avoids bcrypt's 72-byte truncation
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def password_fingerprint(hashed_password: str) -> str:
    """Embedded in reset tokens so they become invalid after the password changes (single use)."""
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def create_token(subject: Any, token_type: str = "access", expires_delta: Optional[timedelta] = None,
                 extra: Optional[dict] = None) -> str:
    if expires_delta is None:
        minutes = {
            "access": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "reset": settings.RESET_TOKEN_EXPIRE_MINUTES,
            "verify": settings.VERIFY_TOKEN_EXPIRE_MINUTES,
        }.get(token_type, settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        expires_delta = timedelta(minutes=minutes)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: Any, expires_delta: Optional[timedelta] = None) -> str:
    return create_token(subject, "access", expires_delta)


def decode_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None
    if payload.get("type", "access") != expected_type:
        return None
    return payload


# backwards compatible name
def decode_access_token(token: str) -> Optional[dict]:
    return decode_token(token, "access")
