from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request, WebSocket
from sqlalchemy.orm import Session

from .auth_security import TokenError, decode_access_token
from .db import SessionLocal
from .models import User
from .settings import settings


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_client_ip(request: Request) -> str | None:
    xff = request.headers.get('x-forwarded-for')
    if xff:
        first = xff.split(',')[0].strip()
        return first or None
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str | None:
    ua = request.headers.get('user-agent', '').strip()
    return ua[:255] if ua else None


def _load_user_by_access_token(db: Session, access_token: str | None) -> User | None:
    if not access_token:
        return None
    try:
        payload = decode_access_token(access_token)
    except TokenError:
        return None
    user_id = str(payload.get('sub') or '')
    if not user_id:
        return None
    return db.get(User, user_id)


def get_current_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=settings.COOKIE_ACCESS_NAME),
) -> User:
    user = _load_user_by_access_token(db, access_token)
    if not user:
        raise HTTPException(status_code=401, detail='UNAUTHORIZED')
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if user.status != 'ACTIVE':
        raise HTTPException(status_code=403, detail='ACCOUNT_NOT_ACTIVE')
    return user


def get_optional_user(
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias=settings.COOKIE_ACCESS_NAME),
) -> User | None:
    return _load_user_by_access_token(db, access_token)


def get_ws_current_user(websocket: WebSocket, db: Session) -> User | None:
    token = websocket.cookies.get(settings.COOKIE_ACCESS_NAME)
    return _load_user_by_access_token(db, token)
