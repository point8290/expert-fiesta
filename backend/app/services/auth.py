"""P5-S2 — Authentication helpers: password hashing + JWT access tokens."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET = os.environ.get(
    "AUTH_SECRET", "dev-secret-change-me-in-production-0123456789abcdef"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(hours=24)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_TTL}
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """Return the user id encoded in the token, or None if invalid/expired."""
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM]).get("sub")
    except jwt.PyJWTError:
        return None
