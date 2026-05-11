import os
import unittest
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('DATABASE_URL', 'sqlite:///./test_auth.db')
os.environ.setdefault('JWT_ACCESS_SECRET', 'test-access-secret')
os.environ.setdefault('JWT_REFRESH_SECRET', 'test-refresh-secret')
os.environ.setdefault('NODE_ENV', 'development')
os.environ.setdefault('APP_BASE_URL', 'http://localhost:5173')
os.environ.setdefault('COOKIE_SECURE', 'false')

from fastapi.testclient import TestClient
from sqlalchemy.orm import close_all_sessions

from app.db import Base, SessionLocal, engine, ensure_auth_columns
from app.main import app
from app.models import EmailVerificationToken, PasswordResetToken, RefreshToken, User


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AuthFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        close_all_sessions()
        engine.dispose(close=True)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        ensure_auth_columns()

    def _register(self, email='user@example.com', password='Password1'):
        return self.client.post(
            '/api/auth/register',
            json={
                'email': email,
                'password': password,
                'confirmPassword': password,
            },
        )

    def _extract_token(self, preview_url: str) -> str:
        query = parse_qs(urlparse(preview_url).query)
        token = (query.get('token') or [''])[0]
        self.assertTrue(token)
        return token

    def _verify(self, token: str):
        return self.client.get(f'/api/auth/email/verify?token={token}', follow_redirects=False)

    def _activate_user(self, email='user@example.com', password='Password1'):
        r = self._register(email=email, password=password)
        self.assertEqual(r.status_code, 200)
        token = self._extract_token(r.json()['devEmailPreviewUrl'])
        v = self._verify(token)
        self.assertEqual(v.status_code, 302)

    def test_register_success_creates_pending_user_and_token(self):
        r = self._register()
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['ok'])
        self.assertTrue(body['requiresEmailVerification'])
        self.assertTrue(body.get('devEmailPreviewUrl'))

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == 'user@example.com').one_or_none()
            self.assertIsNotNone(user)
            self.assertEqual(user.status, 'PENDING_EMAIL_VERIFICATION')
            tokens = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).all()
            self.assertEqual(len(tokens), 1)
            self.assertIsNone(tokens[0].used_at)
        finally:
            db.close()

    def test_verify_email_success_activates_user(self):
        r = self._register()
        token = self._extract_token(r.json()['devEmailPreviewUrl'])

        v = self._verify(token)
        self.assertEqual(v.status_code, 302)
        self.assertIn('/login?verified=1', v.headers.get('location', ''))

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == 'user@example.com').one()
            self.assertEqual(user.status, 'ACTIVE')
        finally:
            db.close()

    def test_verify_invalid_and_expired_token(self):
        invalid = self._verify('bad-token')
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()['detail']['error'], 'TOKEN_INVALID')

        r = self._register(email='expired@example.com')
        token = self._extract_token(r.json()['devEmailPreviewUrl'])

        db = SessionLocal()
        try:
            row = db.query(EmailVerificationToken).order_by(EmailVerificationToken.created_at.desc()).first()
            row.expires_at = utc_now() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        expired = self._verify(token)
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.json()['detail']['error'], 'TOKEN_EXPIRED')

    def test_login_lockout_after_failed_attempts(self):
        self._activate_user()

        last = None
        for _ in range(5):
            last = self.client.post(
                '/api/auth/login',
                json={'email': 'user@example.com', 'password': 'Wrong111', 'rememberMe': False},
            )
        self.assertIsNotNone(last)
        self.assertEqual(last.status_code, 423)
        self.assertEqual(last.json()['detail']['error'], 'ACCOUNT_LOCKED')

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == 'user@example.com').one()
            self.assertIsNotNone(user.locked_until)
        finally:
            db.close()

    def test_login_pending_email_verification_returns_403(self):
        self._register(email='pending@example.com')
        login = self.client.post(
            '/api/auth/login',
            json={'email': 'pending@example.com', 'password': 'Password1', 'rememberMe': False},
        )
        self.assertEqual(login.status_code, 403)
        self.assertEqual(login.json()['detail']['error'], 'EMAIL_NOT_VERIFIED')

    def test_remember_me_sets_refresh_cookie_ttl(self):
        self._activate_user(email='remember@example.com')

        short = self.client.post(
            '/api/auth/login',
            json={'email': 'remember@example.com', 'password': 'Password1', 'rememberMe': False},
        )
        self.assertEqual(short.status_code, 200)
        short_cookie = '; '.join(short.headers.get_list('set-cookie'))
        self.assertIn('bc_refresh_token=', short_cookie)
        self.assertIn('Max-Age=43200', short_cookie)

        long = self.client.post(
            '/api/auth/login',
            json={'email': 'remember@example.com', 'password': 'Password1', 'rememberMe': True},
        )
        self.assertEqual(long.status_code, 200)
        long_cookie = '; '.join(long.headers.get_list('set-cookie'))
        self.assertIn('bc_refresh_token=', long_cookie)
        self.assertIn('Max-Age=2592000', long_cookie)

    def test_reset_request_is_always_ok(self):
        r = self.client.post('/api/auth/password/reset/request', json={'email': 'ghost@example.com'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])

    def test_reset_confirm_invalidates_all_refresh_tokens(self):
        self._activate_user(email='reset@example.com')

        login = self.client.post(
            '/api/auth/login',
            json={'email': 'reset@example.com', 'password': 'Password1', 'rememberMe': True},
        )
        self.assertEqual(login.status_code, 200)

        reset_req = self.client.post('/api/auth/password/reset/request', json={'email': 'reset@example.com'})
        self.assertEqual(reset_req.status_code, 200)
        reset_token = self._extract_token(reset_req.json()['devEmailPreviewUrl'])

        confirm = self.client.post(
            '/api/auth/password/reset/confirm',
            json={
                'token': reset_token,
                'newPassword': 'Newpass123',
                'confirmPassword': 'Newpass123',
            },
        )
        self.assertEqual(confirm.status_code, 200)

        refresh = self.client.post('/api/auth/refresh', json={})
        self.assertEqual(refresh.status_code, 401)

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == 'reset@example.com').one()
            active_refresh = (
                db.query(RefreshToken)
                .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
                .all()
            )
            self.assertEqual(active_refresh, [])
            used_reset = (
                db.query(PasswordResetToken)
                .filter(PasswordResetToken.user_id == user.id)
                .order_by(PasswordResetToken.created_at.desc())
                .first()
            )
            self.assertIsNotNone(used_reset.used_at)
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()
