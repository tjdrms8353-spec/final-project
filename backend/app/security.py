import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from .config import TOKEN_TTL_HOURS


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """토큰은 DB에 해시로만 저장한다 (유출 시 원문 복원 불가)."""
    return hashlib.sha256(token.encode()).hexdigest()


def token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)
