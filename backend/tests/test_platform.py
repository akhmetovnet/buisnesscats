import os
import unittest
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

os.environ.setdefault('DATABASE_URL', 'sqlite:///./test_platform.db')
os.environ.setdefault('JWT_ACCESS_SECRET', 'test-access-secret')
os.environ.setdefault('JWT_REFRESH_SECRET', 'test-refresh-secret')
os.environ.setdefault('NODE_ENV', 'development')
os.environ.setdefault('APP_BASE_URL', 'http://localhost:5173')
os.environ.setdefault('COOKIE_SECURE', 'false')

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine, ensure_auth_columns, ensure_platform_columns
from app.main import app
from app.models import GameSession, Season, TradeRequest


class PlatformFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        ensure_auth_columns()
        ensure_platform_columns()

    def _extract_token(self, preview_url: str) -> str:
        query = parse_qs(urlparse(preview_url).query)
        return (query.get('token') or [''])[0]

    def _register_verify_login(self, email='candidate@example.com', password='Password1'):
        reg = self.client.post('/api/auth/register', json={'email': email, 'password': password, 'confirmPassword': password})
        self.assertEqual(reg.status_code, 200)
        token = self._extract_token(reg.json()['devEmailPreviewUrl'])
        verify = self.client.get(f'/api/auth/email/verify?token={token}', follow_redirects=False)
        self.assertEqual(verify.status_code, 302)
        login = self.client.post('/api/auth/login', json={'email': email, 'password': password, 'rememberMe': True})
        self.assertEqual(login.status_code, 200)

    def test_profile_update_and_avatar_upload_delete(self):
        self._register_verify_login()

        profile = self.client.patch(
            '/api/me/profile',
            json={
                'firstName': 'Тимур',
                'lastName': 'Ахметов',
                'middleName': 'М',
                'birthDate': '2000-01-01',
                'birthPlace': 'Казань',
                'city': 'Москва',
                'educationType': 'Университет',
                'educationPlace': 'МГУ',
                'directions': ['Аналитика', 'Менеджмент'],
                'university': 'МГУ',
                'eventCode': 'BC-2026',
                'desiredSpecialties': 'Product, Analytics',
            },
        )
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()['firstName'], 'Тимур')

        upload = self.client.post(
            '/api/me/avatar',
            files={'file': ('avatar.png', b'fake-image-content', 'image/png')},
        )
        self.assertEqual(upload.status_code, 200)
        self.assertTrue(upload.json().get('avatarUrl', '').startswith('/uploads/avatars/'))

        delete = self.client.delete('/api/me/avatar')
        self.assertEqual(delete.status_code, 200)
        self.assertIsNone(delete.json().get('avatarUrl'))

    def test_single_active_session_rule(self):
        self._register_verify_login(email='active@example.com')

        first = self.client.post('/api/sessions/start')
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['created'])
        session_id = first.json()['sessionId']

        second = self.client.post('/api/sessions/start')
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()['created'])
        self.assertEqual(second.json()['sessionId'], session_id)

        active = self.client.get('/api/sessions/active')
        self.assertEqual(active.status_code, 200)
        self.assertTrue(active.json()['hasActive'])

        finish = self.client.post('/api/game/session/finish', json={'sessionId': session_id})
        self.assertEqual(finish.status_code, 200)

        active_after = self.client.get('/api/sessions/active')
        self.assertEqual(active_after.status_code, 200)
        self.assertFalse(active_after.json()['hasActive'])

    def test_competency_floor_is_one(self):
        self._register_verify_login(email='floor@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            season = (
                db.query(Season)
                .filter(Season.session_id == session_id, Season.season_number == 1)
                .first()
            )
            season.coins_end = 0
            season.bot_coins_end = 100
            session.status = 'active'
            db.commit()
        finally:
            db.close()

        finish = self.client.post('/api/game/session/finish', json={'sessionId': session_id})
        self.assertEqual(finish.status_code, 200)

        summary = self.client.get('/api/competencies/summary')
        self.assertEqual(summary.status_code, 200)
        items = summary.json()['items']
        self.assertTrue(items)
        for item in items:
            self.assertGreaterEqual(float(item['level']), 1.0)

    def test_inactivity_timeout_forces_bankrupt_completed(self):
        self._register_verify_login(email='inactive@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inactive_timeout_at = datetime.utcnow() - timedelta(seconds=1)
            session.last_action_at = datetime.utcnow() - timedelta(minutes=6)
            db.commit()
        finally:
            db.close()

        state = self.client.get(f'/api/game/state/{session_id}/1')
        self.assertEqual(state.status_code, 409)
        self.assertEqual(state.json()['detail']['error'], 'INACTIVITY_TIMEOUT')

        history = self.client.get('/api/sessions/history')
        self.assertEqual(history.status_code, 200)
        items = history.json().get('items', [])
        self.assertTrue(items)
        item = next((it for it in items if it['id'] == session_id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['status'], 'BANKRUPT_COMPLETED')
        self.assertEqual(item['finalPlace'], 24)
        self.assertEqual(item['bankruptReason'], 'INACTIVITY')

    def test_new_session_does_not_seed_trade_request_on_initial_fetch(self):
        self._register_verify_login(email='fresh-session@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        requests_response = self.client.get(f'/api/game/trade-requests/{session_id}/1')
        self.assertEqual(requests_response.status_code, 200)
        self.assertEqual(requests_response.json().get('items'), [])

        db = SessionLocal()
        try:
            count = db.query(TradeRequest).filter(TradeRequest.session_id == session_id).count()
            self.assertEqual(count, 0)
        finally:
            db.close()

    def test_trade_request_list_processes_due_bot_response(self):
        self._register_verify_login(email='bot-response@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': 'ginger',
                        'catType': 'ginger',
                        'catColor': 'ginger',
                        'catSex': 'M',
                        'proposedPrice': 8,
                        'unitPrice': 8,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'BUY',
                    }
                ],
            },
        )
        self.assertEqual(send.status_code, 200)
        request_id = send.json()['request']['id']

        db = SessionLocal()
        try:
            req = db.get(TradeRequest, request_id)
            req.updated_at = datetime.utcnow() - timedelta(seconds=10)
            db.commit()
        finally:
            db.close()

        requests_response = self.client.get(f'/api/game/trade-requests/{session_id}/1')
        self.assertEqual(requests_response.status_code, 200)
        items = requests_response.json().get('items', [])
        self.assertTrue(items)
        self.assertNotEqual(items[0]['status'], 'PENDING_OUTGOING')


if __name__ == '__main__':
    unittest.main()
