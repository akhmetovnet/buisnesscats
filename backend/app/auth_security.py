from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .settings import settings

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


class TokenError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_email(email: str) -> str:
    return str(email or '').strip().lower()


def hash_email(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode('utf-8')).hexdigest()


def validate_password_strength(password: str) -> bool:
    if not isinstance(password, str):
        return False
    return bool(PASSWORD_RE.match(password))


def hash_password(password: str) -> str:
    data = password.encode('utf-8')
    return bcrypt.hashpw(data, bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def generate_token_value() -> str:
    return secrets.token_urlsafe(48)


def hash_token_value(token: str) -> str:
    return hashlib.sha256(str(token).encode('utf-8')).hexdigest()


def create_access_token(user_id: str) -> str:
    exp = utcnow() + timedelta(minutes=settings.ACCESS_TTL_MINUTES)
    payload = {
        'sub': str(user_id),
        'typ': 'access',
        'exp': exp,
        'iat': utcnow(),
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm='HS256')


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=['HS256'])
    except Exception as exc:
        raise TokenError('invalid_access_token') from exc

    if payload.get('typ') != 'access' or not payload.get('sub'):
        raise TokenError('invalid_access_token')
    return payload


def refresh_expiry(remember_me: bool) -> datetime:
    if remember_me:
        return utcnow() + timedelta(days=settings.REFRESH_TTL_DAYS_REMEMBER)
    return utcnow() + timedelta(hours=settings.REFRESH_TTL_HOURS)


def cookie_max_age_seconds(remember_me: bool) -> int:
    if remember_me:
        return int(timedelta(days=settings.REFRESH_TTL_DAYS_REMEMBER).total_seconds())
    return int(timedelta(hours=settings.REFRESH_TTL_HOURS).total_seconds())
