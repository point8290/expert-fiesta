"""P5-S2 — Authentication helpers: password hashing + JWT access tokens."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import get_settings

ALGORITHM = "HS256"


def _secret() -> str:
    return get_settings().auth_secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    ttl = timedelta(minutes=get_settings().access_token_minutes)
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """Return the user id encoded in the token, or None if invalid/expired."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM]).get("sub")
    except jwt.PyJWTError:
        return None
