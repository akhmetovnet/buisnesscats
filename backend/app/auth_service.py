from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from .auth_security import (
    cookie_max_age_seconds,
    create_access_token,
    generate_token_value,
    hash_email,
    hash_password,
    hash_token_value,
    normalize_email,
    refresh_expiry,
    validate_password_strength,
    verify_password,
)
from .email_provider import get_email_provider
from .models import (
    AuditLog,
    AuthRateLimit,
    CandidateProfile,
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)
from .settings import settings


VERIFY_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(minutes=45)


@dataclass
class AuthError(Exception):
    status_code: int
    error_code: str
    message: str
    retry_after_seconds: int | None = None


@dataclass
class SessionTokens:
    access_token: str
    refresh_token: str
    refresh_max_age: int


@dataclass
class LoginResult:
    user: User
    tokens: SessionTokens


@dataclass
class RegisterResult:
    preview_url: str | None


@dataclass
class GenericResult:
    preview_url: str | None


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _audit(
    db: Session,
    *,
    event_type: str,
    user_id: str | None,
    email: str | None,
    ip: str | None,
    user_agent: str | None,
    result_code: str,
) -> None:
    db.add(
        AuditLog(
            event_type=event_type,
            user_id=user_id,
            email_hash=hash_email(email) if email else None,
            ip=ip,
            user_agent=(user_agent or '')[:255] or None,
            result_code=result_code,
        )
    )


def _upsert_rate_limit(db: Session, action: str, key: str, window_seconds: int) -> AuthRateLimit:
    rec = (
        db.query(AuthRateLimit)
        .filter(AuthRateLimit.action == action, AuthRateLimit.key == key)
        .one_or_none()
    )
    now = _now()
    if not rec:
        rec = AuthRateLimit(action=action, key=key, count=0, window_start=now)
        db.add(rec)
        db.flush()
        return rec

    if (now - rec.window_start).total_seconds() >= window_seconds:
        rec.window_start = now
        rec.count = 0
    return rec


def enforce_rate_limit(
    db: Session,
    *,
    action: str,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    rec = _upsert_rate_limit(db, action, key, window_seconds)
    now = _now()
    if rec.count >= limit:
        retry = max(1, int(window_seconds - (now - rec.window_start).total_seconds()))
        raise AuthError(status_code=429, error_code='RATE_LIMITED', message='Rate limit exceeded', retry_after_seconds=retry)
    rec.count += 1


def _clear_rate_limit(db: Session, action: str, key: str) -> None:
    rec = (
        db.query(AuthRateLimit)
        .filter(AuthRateLimit.action == action, AuthRateLimit.key == key)
        .one_or_none()
    )
    if rec:
        db.delete(rec)


def _new_email_verification_token(db: Session, user_id: str) -> str:
    token = generate_token_value()
    db.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_token_value(token),
            expires_at=_now() + VERIFY_TOKEN_TTL,
        )
    )
    return token


def _new_password_reset_token(db: Session, user_id: str) -> str:
    token = generate_token_value()
    db.add(
        PasswordResetToken(
            user_id=user_id,
            token_hash=hash_token_value(token),
            expires_at=_now() + RESET_TOKEN_TTL,
        )
    )
    return token


def _issue_refresh_token(
    db: Session,
    *,
    user_id: str,
    remember_me: bool,
    ip: str | None,
    user_agent: str | None,
) -> tuple[str, RefreshToken]:
    raw = generate_token_value()
    rec = RefreshToken(
        user_id=user_id,
        jti=secrets.token_hex(16),
        token_hash=hash_token_value(raw),
        expires_at=refresh_expiry(remember_me),
        user_agent=(user_agent or '')[:255] or None,
        ip=ip,
        remember_me=remember_me,
    )
    db.add(rec)
    db.flush()
    return raw, rec


def _session_tokens(
    *,
    user_id: str,
    refresh_token: str,
    remember_me: bool,
) -> SessionTokens:
    return SessionTokens(
        access_token=create_access_token(user_id),
        refresh_token=refresh_token,
        refresh_max_age=cookie_max_age_seconds(remember_me),
    )


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    confirm_password: str,
    ip: str | None,
    user_agent: str | None,
) -> RegisterResult:
    normalized_email = normalize_email(email)
    enforce_rate_limit(db, action='AUTH_REGISTER', key=f'ip:{ip or "unknown"}', limit=3, window_seconds=3600)

    if password != confirm_password:
        raise AuthError(400, 'VALIDATION_ERROR', 'Passwords do not match')
    if not validate_password_strength(password):
        raise AuthError(400, 'VALIDATION_ERROR', 'Password must be at least 8 chars and contain letters and digits')

    existing = db.query(User).filter(User.email == normalized_email).one_or_none()
    if existing:
        _audit(
            db,
            event_type='AUTH_REGISTER',
            user_id=existing.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='EMAIL_TAKEN',
        )
        raise AuthError(409, 'EMAIL_TAKEN', 'Account already exists')

    user = User(
        role='candidate',
        account_role='USER',
        email=normalized_email,
        password_hash=hash_password(password),
        status='PENDING_EMAIL_VERIFICATION',
        display_name=normalized_email.split('@', 1)[0],
    )
    db.add(user)
    db.flush()

    profile = CandidateProfile(
        user_id=user.id,
        full_name=user.display_name or '',
        skills_json='[]',
        updated_at=_now(),
    )
    db.add(profile)

    raw_token = _new_email_verification_token(db, user.id)
    verify_link = f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={raw_token}"
    preview = get_email_provider().send_verification_email(normalized_email, verify_link).preview_url

    _audit(
        db,
        event_type='AUTH_REGISTER',
        user_id=user.id,
        email=normalized_email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    _audit(
        db,
        event_type='AUTH_VERIFY_EMAIL_SENT',
        user_id=user.id,
        email=normalized_email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()
    return RegisterResult(preview_url=preview if settings.dev_email_preview_enabled else None)


def resend_verification_email(
    db: Session,
    *,
    email: str,
    ip: str | None,
    user_agent: str | None,
) -> GenericResult:
    normalized_email = normalize_email(email)
    enforce_rate_limit(db, action='AUTH_VERIFY_RESEND', key=f'email:{normalized_email}', limit=3, window_seconds=3600)

    user = db.query(User).filter(User.email == normalized_email).one_or_none()
    preview: str | None = None
    if user and user.status == 'PENDING_EMAIL_VERIFICATION':
        raw_token = _new_email_verification_token(db, user.id)
        verify_link = f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={raw_token}"
        preview = get_email_provider().send_verification_email(normalized_email, verify_link).preview_url
        _audit(
            db,
            event_type='AUTH_VERIFY_EMAIL_SENT',
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='OK',
        )
    db.commit()
    return GenericResult(preview_url=preview if settings.dev_email_preview_enabled else None)


def verify_email_token(db: Session, *, token: str, ip: str | None, user_agent: str | None) -> User:
    hashed = hash_token_value(token)
    row = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == hashed, EmailVerificationToken.used_at.is_(None))
        .order_by(EmailVerificationToken.created_at.desc())
        .first()
    )
    if not row:
        raise AuthError(400, 'TOKEN_INVALID', 'Invalid token')

    now = _now()
    if row.expires_at < now:
        raise AuthError(410, 'TOKEN_EXPIRED', 'Token expired')

    user = db.get(User, row.user_id)
    if not user:
        raise AuthError(400, 'TOKEN_INVALID', 'Invalid token')

    row.used_at = now
    user.status = 'ACTIVE'
    _audit(
        db,
        event_type='AUTH_VERIFY_EMAIL_SUCCESS',
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()
    return user


def login_user(
    db: Session,
    *,
    email: str,
    password: str,
    remember_me: bool,
    ip: str | None,
    user_agent: str | None,
) -> LoginResult:
    normalized_email = normalize_email(email)
    login_fail_key = f"{ip or 'unknown'}:{normalized_email}"

    user = db.query(User).filter(User.email == normalized_email).one_or_none()
    now = _now()

    if user and user.locked_until and user.locked_until > now:
        retry_after = max(1, int((user.locked_until - now).total_seconds()))
        _audit(
            db,
            event_type='AUTH_LOCKED',
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='LOCKED',
        )
        db.commit()
        raise AuthError(423, 'ACCOUNT_LOCKED', 'Too many attempts. Try later.', retry_after_seconds=retry_after)

    password_ok = bool(user and verify_password(password, user.password_hash))
    if not password_ok:
        rec = _upsert_rate_limit(db, action='AUTH_LOGIN_FAIL', key=login_fail_key, window_seconds=600)
        rec.count += 1
        _audit(
            db,
            event_type='AUTH_LOGIN_FAIL',
            user_id=user.id if user else None,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='INVALID_CREDENTIALS',
        )
        if user and rec.count >= 5:
            user.locked_until = now + timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
            db.commit()
            retry_after = int(timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES).total_seconds())
            raise AuthError(423, 'ACCOUNT_LOCKED', 'Too many attempts. Try later.', retry_after_seconds=retry_after)

        retry_after = max(1, int(600 - (now - rec.window_start).total_seconds())) if rec.count >= 5 else None
        db.commit()
        if rec.count >= 5:
            raise AuthError(429, 'RATE_LIMITED', 'Too many attempts. Try later.', retry_after_seconds=retry_after)
        raise AuthError(401, 'INVALID_CREDENTIALS', 'Invalid email or password')

    if user.status == 'PENDING_EMAIL_VERIFICATION':
        _audit(
            db,
            event_type='AUTH_LOGIN_FAIL',
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='EMAIL_NOT_VERIFIED',
        )
        db.commit()
        raise AuthError(403, 'EMAIL_NOT_VERIFIED', 'Confirm your email first')

    if user.status in {'DISABLED'}:
        _audit(
            db,
            event_type='AUTH_LOGIN_FAIL',
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='INVALID_CREDENTIALS',
        )
        db.commit()
        raise AuthError(401, 'INVALID_CREDENTIALS', 'Invalid email or password')

    user.locked_until = None
    user.last_login_at = now
    _clear_rate_limit(db, action='AUTH_LOGIN_FAIL', key=login_fail_key)

    refresh_value, _ = _issue_refresh_token(
        db,
        user_id=user.id,
        remember_me=remember_me,
        ip=ip,
        user_agent=user_agent,
    )
    tokens = _session_tokens(user_id=user.id, refresh_token=refresh_value, remember_me=remember_me)
    _audit(
        db,
        event_type='AUTH_LOGIN_SUCCESS',
        user_id=user.id,
        email=normalized_email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()
    return LoginResult(user=user, tokens=tokens)


def refresh_session(
    db: Session,
    *,
    refresh_token: str | None,
    ip: str | None,
    user_agent: str | None,
) -> SessionTokens:
    if not refresh_token:
        raise AuthError(401, 'INVALID_REFRESH', 'Invalid refresh token')

    now = _now()
    rec = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token_value(refresh_token))
        .one_or_none()
    )
    if not rec or rec.revoked_at is not None or rec.expires_at < now:
        raise AuthError(401, 'INVALID_REFRESH', 'Invalid refresh token')

    user = db.get(User, rec.user_id)
    if not user or user.status != 'ACTIVE':
        raise AuthError(401, 'INVALID_REFRESH', 'Invalid refresh token')

    new_raw, new_rec = _issue_refresh_token(
        db,
        user_id=user.id,
        remember_me=bool(rec.remember_me),
        ip=ip,
        user_agent=user_agent,
    )
    rec.revoked_at = now
    rec.replaced_by_token_id = new_rec.id
    db.commit()

    return _session_tokens(user_id=user.id, refresh_token=new_raw, remember_me=bool(rec.remember_me))


def logout_session(db: Session, *, refresh_token: str | None, user_id: str | None, ip: str | None, user_agent: str | None) -> None:
    if refresh_token:
        rec = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == hash_token_value(refresh_token))
            .one_or_none()
        )
        if rec and rec.revoked_at is None:
            rec.revoked_at = _now()
    _audit(
        db,
        event_type='AUTH_LOGOUT',
        user_id=user_id,
        email=None,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()


def logout_all_sessions(db: Session, *, user_id: str, ip: str | None, user_agent: str | None) -> None:
    now = _now()
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .update({'revoked_at': now}, synchronize_session=False)
    )
    _audit(
        db,
        event_type='AUTH_LOGOUT_ALL',
        user_id=user_id,
        email=None,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()


def request_password_reset(db: Session, *, email: str, ip: str | None, user_agent: str | None) -> GenericResult:
    normalized_email = normalize_email(email)
    enforce_rate_limit(db, action='AUTH_RESET_REQUEST', key=f'email:{normalized_email}', limit=3, window_seconds=3600)

    user = db.query(User).filter(User.email == normalized_email).one_or_none()
    preview: str | None = None
    if user:
        raw_token = _new_password_reset_token(db, user.id)
        reset_link = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={raw_token}"
        preview = get_email_provider().send_password_reset_email(normalized_email, reset_link).preview_url
        _audit(
            db,
            event_type='AUTH_RESET_REQUESTED',
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            result_code='OK',
        )
    db.commit()
    return GenericResult(preview_url=preview if settings.dev_email_preview_enabled else None)


def confirm_password_reset(
    db: Session,
    *,
    token: str,
    new_password: str,
    confirm_password: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    if new_password != confirm_password:
        raise AuthError(400, 'VALIDATION_ERROR', 'Passwords do not match')
    if not validate_password_strength(new_password):
        raise AuthError(400, 'VALIDATION_ERROR', 'Password must be at least 8 chars and contain letters and digits')

    hashed = hash_token_value(token)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hashed, PasswordResetToken.used_at.is_(None))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if not row:
        raise AuthError(400, 'TOKEN_INVALID', 'Invalid token')
    if row.expires_at < _now():
        raise AuthError(410, 'TOKEN_EXPIRED', 'Token expired')

    user = db.get(User, row.user_id)
    if not user:
        raise AuthError(400, 'TOKEN_INVALID', 'Invalid token')

    now = _now()
    row.used_at = now
    user.password_hash = hash_password(new_password)
    user.locked_until = None
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .update({'revoked_at': now}, synchronize_session=False)
    )
    _audit(
        db,
        event_type='AUTH_RESET_COMPLETED',
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    confirm_password: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError(401, 'INVALID_CREDENTIALS', 'Invalid email or password')
    if new_password != confirm_password:
        raise AuthError(400, 'VALIDATION_ERROR', 'Passwords do not match')
    if not validate_password_strength(new_password):
        raise AuthError(400, 'VALIDATION_ERROR', 'Password must be at least 8 chars and contain letters and digits')

    user.password_hash = hash_password(new_password)
    user.locked_until = None
    now = _now()
    (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .update({'revoked_at': now}, synchronize_session=False)
    )
    _audit(
        db,
        event_type='AUTH_RESET_COMPLETED',
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        result_code='OK',
    )
    db.commit()


def get_me_payload(user: User) -> dict:
    display_name = user.display_name
    if not display_name:
        display_name = " ".join([part for part in [user.first_name, user.last_name] if part]).strip() or (user.email or '')
    return {
        'id': user.id,
        'email': user.email or '',
        'status': user.status,
        'role': user.account_role or 'USER',
        'displayName': display_name,
        'avatarUrl': user.avatar_url,
    }
