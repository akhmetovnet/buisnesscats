import json
import math
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

from app import crud
from app.db import Base, SessionLocal, engine, ensure_auth_columns, ensure_platform_columns
from app.game_config import CONFIG_START_COINS
from app.main import app
from app.models import GameEvent, GameProgress, GameSession, Season, SessionCompetencyDelta, TradeBotState, TradeRequest


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

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

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

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

    def test_money_bankruptcy_finalizes_session_and_blocks_reentry(self):
        self._register_verify_login(email='money-loss@example.com')

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
            season.bot_coins_end = 91
            season.ended_at = datetime.utcnow()
            session.status = 'active'
            session.result_coins_player = 0
            session.result_coins_bot = 91
            db.add(
                Season(
                    session_id=session_id,
                    season_number=2,
                    coins_start=0,
                    coins_end=3,
                    profit=0,
                    bot_coins_end=91,
                )
            )
            db.add(
                GameProgress(
                    session_id=session_id,
                    season_number=2,
                    nursery_json='{"coins":3}',
                    nursery_coins_delta=3,
                    time_left=120,
                )
            )
            db.commit()
        finally:
            db.close()

    def test_finish_season_uses_nursery_delta_and_finalizes_bankruptcy(self):
        self._register_verify_login(email='season-bankrupt@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        finish = self.client.post(
            '/api/game/season/finish',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'finishEarly': False,
                'nursery': {
                    'coins': 0,
                    'cats': [],
                    'home': {
                        'parents': {'left': [None, None], 'right': [None, None]},
                        'kittens': [],
                    },
                },
                'nurseryCoinsDelta': -(CONFIG_START_COINS + 40),
            },
        )
        self.assertEqual(finish.status_code, 200)
        season_result = finish.json()['seasonResult']
        self.assertTrue(season_result['terminal'])
        self.assertEqual(season_result['sessionStatus'], 'BANKRUPT_COMPLETED')
        self.assertEqual(season_result['completionReason'], 'BANKRUPT_MONEY')
        self.assertEqual(int(season_result['coinsEnd']), 0)

        active = self.client.get('/api/sessions/active')
        self.assertEqual(active.status_code, 200)
        self.assertFalse(active.json()['hasActive'])

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

        details = self.client.get(f'/api/sessions/{session_id}/details')
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()['status'], 'BANKRUPT_COMPLETED')
        self.assertEqual(details.json()['reasonCompleted'], 'BANKRUPT_MONEY')

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            self.assertEqual(session.status, 'bankrupt_completed')
            self.assertEqual(session.final_balance, 0)

            season = (
                db.query(Season)
                .filter(Season.session_id == session_id, Season.season_number == 1)
                .first()
            )
            self.assertIsNotNone(season)
            self.assertEqual(int(season.coins_end or 0), 0)
            meta = json.loads(season.meta_json or '{}')
            self.assertGreater(int(meta.get('backendCoinsEnd', 0)), 0)
            expected_delta = -(CONFIG_START_COINS + 40)
            self.assertEqual(int(meta.get('nurseryCoinsDeltaApplied', 0)), expected_delta)
            self.assertEqual(
                int(meta.get('effectiveCoinsEnd', 0)),
                max(0, int(meta.get('backendCoinsEnd', 0)) + expected_delta),
            )

            next_season = (
                db.query(Season)
                .filter(Season.session_id == session_id, Season.season_number == 2)
                .first()
            )
            self.assertIsNone(next_season)
        finally:
            db.close()

    def test_active_endpoint_finalizes_legacy_broken_bankruptcy_from_progress(self):
        self._register_verify_login(email='legacy-bankrupt@example.com')

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
            season.coins_end = 11
            season.bot_coins_end = 73
            season.ended_at = datetime.utcnow()
            session.status = 'active'
            session.result_coins_player = 11
            session.result_coins_bot = 73
            db.add(
                Season(
                    session_id=session_id,
                    season_number=2,
                    coins_start=11,
                    coins_end=11,
                    profit=0,
                    bot_coins_end=73,
                )
            )
            db.add(
                GameProgress(
                    session_id=session_id,
                    season_number=1,
                    nursery_json='{"coins":0}',
                    nursery_coins_delta=-20,
                    time_left=10,
                )
            )
            db.commit()
        finally:
            db.close()

        active = self.client.get('/api/sessions/active')
        self.assertEqual(active.status_code, 200)
        self.assertFalse(active.json()['hasActive'])

        state = self.client.get(f'/api/game/state/{session_id}/2')
        self.assertEqual(state.status_code, 409)
        self.assertEqual(state.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

        details = self.client.get(f'/api/sessions/{session_id}/details')
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()['status'], 'BANKRUPT_COMPLETED')
        self.assertEqual(details.json()['finalBalance'], 0)

        history = self.client.get('/api/sessions/history')
        self.assertEqual(history.status_code, 200)
        items = history.json().get('items', [])
        item = next((it for it in items if it['id'] == session_id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['status'], 'BANKRUPT_COMPLETED')
        self.assertEqual(item['reasonCompleted'], 'BANKRUPT_MONEY')
        self.assertEqual(item['finalPlace'], 24)

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            self.assertEqual(session.status, 'bankrupt_completed')
            self.assertEqual(session.final_place, 24)
            self.assertEqual(session.final_balance, 0)
            self.assertEqual(session.finish_reason, 'BANKRUPT_MONEY')
            self.assertEqual(session.season_count_completed, 1)
            self.assertIsNotNone(session.finished_at)

            progress_count = db.query(GameProgress).filter(GameProgress.session_id == session_id).count()
            self.assertEqual(progress_count, 0)

            delta = (
                db.query(SessionCompetencyDelta)
                .filter(SessionCompetencyDelta.session_id == session_id)
                .one_or_none()
            )
            self.assertIsNotNone(delta)
        finally:
            db.close()

    def test_active_endpoint_finalizes_legacy_completed_session_after_last_season(self):
        self._register_verify_login(email='legacy-season-13@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            base_season = (
                db.query(Season)
                .filter(Season.session_id == session_id, Season.season_number == 1)
                .first()
            )
            self.assertIsNotNone(base_season)
            base_season.coins_start = 40
            base_season.coins_end = 42
            base_season.profit = 2
            base_season.bot_coins_end = 38
            base_season.ended_at = datetime.utcnow() - timedelta(days=12)

            for season_number in range(2, 14):
                db.add(
                    Season(
                        session_id=session_id,
                        season_number=season_number,
                        coins_start=40 + season_number,
                        coins_end=42 + season_number,
                        profit=2,
                        bot_coins_end=35 + season_number,
                        ended_at=datetime.utcnow() - timedelta(days=max(1, 14 - season_number)),
                        meta_json='{}',
                    )
                )

            session.status = 'active'
            session.result_coins_player = 55
            session.result_coins_bot = 48
            session.finished_at = None
            session.finish_reason = None
            session.final_place = None
            session.final_balance = None
            session.season_count_completed = 0
            db.commit()
        finally:
            db.close()

        active = self.client.get('/api/sessions/active')
        self.assertEqual(active.status_code, 200)
        self.assertFalse(active.json()['hasActive'])

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

        details = self.client.get(f'/api/sessions/{session_id}/details')
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()['status'], 'COMPLETED')
        self.assertEqual(details.json()['reasonCompleted'], 'NORMAL_COMPLETION')
        self.assertEqual(details.json()['seasonCountCompleted'], 13)

        history = self.client.get('/api/sessions/history')
        self.assertEqual(history.status_code, 200)
        item = next((it for it in history.json().get('items', []) if it['id'] == session_id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['status'], 'COMPLETED')
        self.assertEqual(item['reasonCompleted'], 'NORMAL_COMPLETION')

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            self.assertEqual(session.status, 'completed')
            self.assertEqual(session.finish_reason, 'SEASONS_COMPLETED')
            self.assertEqual(session.season_count_completed, 13)
            self.assertIsNotNone(session.finished_at)
        finally:
            db.close()

    def test_last_season_finalizes_completed_session_and_returns_leaderboard(self):
        self._register_verify_login(email='season-13@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            base_season = (
                db.query(Season)
                .filter(Season.session_id == session_id, Season.season_number == 1)
                .first()
            )
            self.assertIsNotNone(base_season)
            base_season.coins_start = 40
            base_season.coins_end = 42
            base_season.profit = 2
            base_season.bot_coins_end = 38
            base_season.ended_at = datetime.utcnow() - timedelta(days=12)

            for season_number in range(2, 13):
                db.add(
                    Season(
                        session_id=session_id,
                        season_number=season_number,
                        coins_start=40 + season_number,
                        coins_end=42 + season_number,
                        profit=2,
                        bot_coins_end=35 + season_number,
                        ended_at=datetime.utcnow() - timedelta(days=max(1, 13 - season_number)),
                        meta_json='{}',
                    )
                )

            db.add(
                Season(
                    session_id=session_id,
                    season_number=13,
                    coins_start=67,
                    coins_end=67,
                    profit=0,
                    bot_coins_end=61,
                    meta_json='{}',
                )
            )
            db.commit()
        finally:
            db.close()

        finish = self.client.post(
            '/api/game/season/finish',
            json={
                'sessionId': session_id,
                'seasonNumber': 13,
                'finishEarly': False,
                'nursery': {
                    'coins': 67,
                    'cats': [],
                    'home': {
                        'parents': {'left': [None, None], 'right': [None, None]},
                        'kittens': [],
                    },
                },
                'nurseryCoinsDelta': 0,
            },
        )
        self.assertEqual(finish.status_code, 200)
        payload = finish.json()
        self.assertIsNone(payload['nextSeason'])
        self.assertTrue(payload['seasonResult']['terminal'])
        self.assertEqual(payload['seasonResult']['sessionStatus'], 'COMPLETED')
        self.assertEqual(payload['seasonResult']['completionReason'], 'NORMAL_COMPLETION')
        self.assertTrue(payload['seasonResult']['completedAllSeasons'])
        self.assertGreater(int(payload['seasonResult']['finalPlace']), 0)
        self.assertGreater(len(payload['seasonResult']['leaderboard']), 0)

        active = self.client.get('/api/sessions/active')
        self.assertEqual(active.status_code, 200)
        self.assertFalse(active.json()['hasActive'])

        continue_response = self.client.post(f'/api/sessions/{session_id}/continue')
        self.assertEqual(continue_response.status_code, 409)
        self.assertEqual(continue_response.json()['detail']['error'], 'SESSION_ALREADY_FINISHED')

        details = self.client.get(f'/api/sessions/{session_id}/details')
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()['status'], 'COMPLETED')
        self.assertEqual(details.json()['reasonCompleted'], 'NORMAL_COMPLETION')
        self.assertEqual(details.json()['seasonCountCompleted'], 13)

        history = self.client.get('/api/sessions/history')
        self.assertEqual(history.status_code, 200)
        item = next((it for it in history.json().get('items', []) if it['id'] == session_id), None)
        self.assertIsNotNone(item)
        self.assertEqual(item['status'], 'COMPLETED')
        self.assertEqual(item['reasonCompleted'], 'NORMAL_COMPLETION')

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

    def test_bot_accepts_player_sell_offer_at_display_price_and_executes_trade(self):
        self._register_verify_login(email='bot-buy@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']
        cat_id = 'player-gray-1'

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 0, 'F': 0},
                        'white': {'M': 0, 'F': 0},
                        'gray': {'M': 1, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': cat_id,
                            'color': 'gray',
                            'sex': 'M',
                            'age': 0,
                            'isKitten': True,
                            'hungry': False,
                            'fedThisSeason': True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        market_response = self.client.get(
            f'/api/game/market/{session_id}/1?counterpartyType=shop&counterpartyId=1'
        )
        self.assertEqual(market_response.status_code, 200)
        display_buy_price = int(market_response.json()['market']['gray']['sell'])

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': cat_id,
                        'catType': 'gray',
                        'catColor': 'gray',
                        'catSex': 'M',
                        'proposedPrice': display_buy_price,
                        'unitPrice': display_buy_price,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
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
        request_item = next((item for item in items if item['id'] == request_id), None)
        self.assertIsNotNone(request_item)
        self.assertEqual(request_item['status'], 'ACCEPTED')

        db = SessionLocal()
        try:
            req = db.get(TradeRequest, request_id)
            self.assertEqual(str(req.state), 'ACCEPTED')

            session = db.get(GameSession, session_id)
            inventory = crud._parse_inventory(session.inventory_json or '{}')
            self.assertEqual(inventory['counts']['gray']['M'], 0)
            self.assertEqual(inventory['entities'], [])

            bot_state = (
                db.query(TradeBotState)
                .filter(
                    TradeBotState.session_id == session_id,
                    TradeBotState.bot_player_id == 'shop:1',
                )
                .one()
            )
            bot_inventory = crud._parse_inventory(bot_state.inventory_json or '{}')
            self.assertEqual(bot_state.coins, 240 - display_buy_price)
            self.assertGreaterEqual(bot_inventory['counts']['gray']['M'], 1)

            trade_event = (
                db.query(GameEvent)
                .filter(
                    GameEvent.session_id == session_id,
                    GameEvent.season_number == 1,
                    GameEvent.event_type == 'trade_market',
                )
                .order_by(GameEvent.created_at.desc(), GameEvent.id.desc())
                .first()
            )
            self.assertIsNotNone(trade_event)
            payload = json.loads(trade_event.payload_json or '{}')
            self.assertEqual(payload.get('action'), 'sell')
            self.assertEqual(payload.get('entityId'), cat_id)
            self.assertEqual(payload.get('unitPrice'), display_buy_price)
        finally:
            db.close()

    def test_animals_outside_house_escape_on_next_season(self):
        self._register_verify_login(email='escape@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 0, 'F': 1},
                        'white': {'M': 0, 'F': 1},
                        'gray': {'M': 1, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': 'yard-adult',
                            'color': 'gray',
                            'sex': 'M',
                            'age': 5,
                            'isKitten': False,
                            'hungry': False,
                            'fedThisSeason': True,
                        },
                        {
                            'id': 'yard-kitten',
                            'color': 'black',
                            'sex': 'F',
                            'age': 0,
                            'isKitten': True,
                            'hungry': False,
                            'fedThisSeason': True,
                        },
                        {
                            'id': 'home-parent',
                            'color': 'white',
                            'sex': 'F',
                            'age': 5,
                            'isKitten': False,
                            'hungry': False,
                            'fedThisSeason': True,
                        },
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        finish = self.client.post(
            '/api/game/season/finish',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'finishEarly': False,
                'nursery': {
                    'coins': 20,
                    'hasHome': True,
                    'cats': [
                        {'id': 'yard-adult', 'color': 'gray', 'sex': 'M', 'age': 5, 'isKitten': False},
                        {'id': 'yard-kitten', 'color': 'black', 'sex': 'F', 'age': 0, 'isKitten': True},
                        {'id': 'home-parent', 'color': 'white', 'sex': 'F', 'age': 5, 'isKitten': False},
                    ],
                    'home': {
                        'parents': {'left': ['home-parent', None], 'right': [None, None]},
                        'kittens': [None] * 12,
                        'breedPending': {'left': False, 'right': False},
                    },
                },
            },
        )
        self.assertEqual(finish.status_code, 200)
        season_result = finish.json()['seasonResult']
        self.assertEqual(season_result['escapedCats'], 2)
        escaped_ids = {item['id'] for item in season_result['escapedAnimals']}
        self.assertEqual(escaped_ids, {'yard-adult', 'yard-kitten'})
        self.assertTrue(all(item['status'] == 'ESCAPED' for item in season_result['escapedAnimals']))

        next_state = self.client.get(f'/api/game/state/{session_id}/2')
        self.assertEqual(next_state.status_code, 200)
        next_entities = next_state.json()['inventoryEntities']
        self.assertEqual([item['id'] for item in next_entities], ['home-parent'])
        self.assertEqual(next_entities[0]['age'], 6)

    def test_adult_trade_request_is_rejected_by_backend(self):
        self._register_verify_login(email='adult-trade@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 1, 'F': 0},
                        'white': {'M': 0, 'F': 0},
                        'gray': {'M': 0, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': 'adult-black-1',
                            'color': 'black',
                            'sex': 'M',
                            'age': 5,
                            'isKitten': False,
                            'hungry': False,
                            'fedThisSeason': True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': 'adult-black-1',
                        'catType': 'black',
                        'catColor': 'black',
                        'catSex': 'M',
                        'proposedPrice': 8,
                        'unitPrice': 8,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(send.status_code, 200)
        self.assertFalse(send.json()['ok'])
        self.assertEqual(send.json()['error'], 'ONLY_KITTENS_CAN_BE_TRADED')

        db = SessionLocal()
        try:
            count = db.query(TradeRequest).filter(TradeRequest.session_id == session_id).count()
            self.assertEqual(count, 0)
        finally:
            db.close()

    def test_adult_trade_request_is_rejected_even_with_stale_kitten_flag(self):
        self._register_verify_login(email='adult-trade-stale-flag@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 1, 'F': 0},
                        'white': {'M': 0, 'F': 0},
                        'gray': {'M': 0, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': 'adult-black-stale-flag',
                            'color': 'black',
                            'sex': 'M',
                            'age': 3,
                            'isKitten': True,
                            'hungry': False,
                            'fedThisSeason': True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': 'adult-black-stale-flag',
                        'catType': 'black',
                        'catColor': 'black',
                        'catSex': 'M',
                        'proposedPrice': 8,
                        'unitPrice': 8,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(send.status_code, 200)
        self.assertFalse(send.json()['ok'])
        self.assertEqual(send.json()['error'], 'ONLY_KITTENS_CAN_BE_TRADED')

        db = SessionLocal()
        try:
            count = db.query(TradeRequest).filter(TradeRequest.session_id == session_id).count()
            self.assertEqual(count, 0)
        finally:
            db.close()

    def test_clarify_action_creates_next_request_version_in_thread(self):
        self._register_verify_login(email='clarify-version@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 0, 'F': 0},
                        'white': {'M': 0, 'F': 0},
                        'gray': {'M': 1, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': 'clarify-gray-1',
                            'color': 'gray',
                            'sex': 'M',
                            'age': 0,
                            'isKitten': True,
                            'hungry': False,
                            'fedThisSeason': True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        market_response = self.client.get(
            f'/api/game/market/{session_id}/1?counterpartyType=shop&counterpartyId=1'
        )
        self.assertEqual(market_response.status_code, 200)
        display_buy_price = int(market_response.json()['market']['gray']['sell'])

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': 'clarify-gray-1',
                        'catType': 'gray',
                        'catColor': 'gray',
                        'catSex': 'M',
                        'proposedPrice': display_buy_price,
                        'unitPrice': display_buy_price,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(send.status_code, 200)
        self.assertTrue(send.json()['ok'])
        original_request_id = send.json()['request']['id']

        db = SessionLocal()
        try:
            req = db.get(TradeRequest, original_request_id)
            req.state = 'NEEDS_CLARIFICATION'
            req.next_actor_player_id = f'user:{db.get(GameSession, session_id).user_id}'
            req.clarification_reason = 'PRICE_OUTDATED'
            req.clarification_meta_json = json.dumps({'message': 'Обновите цену'}, ensure_ascii=False)
            req.message_code = 'REQUIRES_CLARIFICATION'
            db.commit()
        finally:
            db.close()

        clarify = self.client.post(
            f'/api/game/trade-requests/{original_request_id}/action',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'action': 'clarify',
                'counterItems': [
                    {
                        'catId': 'clarify-gray-1',
                        'catType': 'gray',
                        'catColor': 'gray',
                        'catSex': 'M',
                        'proposedPrice': display_buy_price,
                        'unitPrice': display_buy_price,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(clarify.status_code, 200)
        self.assertTrue(clarify.json()['ok'])
        child_request = clarify.json()['request']
        self.assertNotEqual(child_request['id'], original_request_id)
        self.assertEqual(child_request['parentRequestId'], original_request_id)
        self.assertEqual(child_request['threadId'], send.json()['request']['threadId'])
        self.assertEqual(child_request['status'], 'PENDING_OUTGOING')

        db = SessionLocal()
        try:
            archived = db.get(TradeRequest, original_request_id)
            child = db.get(TradeRequest, child_request['id'])
            self.assertEqual(str(archived.state), 'AWAITING_CLARIFICATION')
            self.assertTrue(archived.hidden_by_from)
            self.assertTrue(archived.hidden_by_to)
            self.assertEqual(str(child.parent_request_id), original_request_id)
            self.assertEqual(str(child.thread_id), send.json()['request']['threadId'])
        finally:
            db.close()

    def test_clarified_request_gets_bot_counter_and_does_not_freeze(self):
        self._register_verify_login(email='clarify-counter@example.com')

        start = self.client.post('/api/sessions/start')
        self.assertEqual(start.status_code, 200)
        session_id = start.json()['sessionId']

        db = SessionLocal()
        try:
            session = db.get(GameSession, session_id)
            session.inventory_json = json.dumps(
                {
                    'counts': {
                        'black': {'M': 0, 'F': 0},
                        'white': {'M': 0, 'F': 0},
                        'gray': {'M': 1, 'F': 0},
                        'ginger': {'M': 0, 'F': 0},
                    },
                    'entities': [
                        {
                            'id': 'clarify-gray-2',
                            'color': 'gray',
                            'sex': 'M',
                            'age': 0,
                            'isKitten': True,
                            'hungry': False,
                            'fedThisSeason': True,
                        }
                    ],
                },
                ensure_ascii=False,
            )
            db.commit()
        finally:
            db.close()

        market_response = self.client.get(
            f'/api/game/market/{session_id}/1?counterpartyType=shop&counterpartyId=1'
        )
        self.assertEqual(market_response.status_code, 200)
        display_buy_price = int(market_response.json()['market']['gray']['sell'])
        counter_trigger_price = math.ceil(display_buy_price * 1.10) + 1

        send = self.client.post(
            '/api/game/trade-requests/send',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'counterpartyType': 'shop',
                'counterpartyId': 1,
                'items': [
                    {
                        'catId': 'clarify-gray-2',
                        'catType': 'gray',
                        'catColor': 'gray',
                        'catSex': 'M',
                        'proposedPrice': display_buy_price,
                        'unitPrice': display_buy_price,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(send.status_code, 200)
        original_request_id = send.json()['request']['id']

        db = SessionLocal()
        try:
            user_id = db.get(GameSession, session_id).user_id
            req = db.get(TradeRequest, original_request_id)
            req.state = 'NEEDS_CLARIFICATION'
            req.next_actor_player_id = f'user:{user_id}'
            req.clarification_reason = 'PRICE_OUTDATED'
            req.clarification_meta_json = json.dumps({'message': 'Обновите цену'}, ensure_ascii=False)
            req.message_code = 'REQUIRES_CLARIFICATION'
            db.commit()
        finally:
            db.close()

        clarify = self.client.post(
            f'/api/game/trade-requests/{original_request_id}/action',
            json={
                'sessionId': session_id,
                'seasonNumber': 1,
                'action': 'clarify',
                'counterItems': [
                    {
                        'catId': 'clarify-gray-2',
                        'catType': 'gray',
                        'catColor': 'gray',
                        'catSex': 'M',
                        'proposedPrice': counter_trigger_price,
                        'unitPrice': counter_trigger_price,
                        'quantity': 1,
                        'currency': 'COIN',
                        'side': 'SELL',
                    }
                ],
            },
        )
        self.assertEqual(clarify.status_code, 200)
        self.assertTrue(clarify.json()['ok'])
        child_request_id = clarify.json()['request']['id']

        db = SessionLocal()
        try:
            req = db.get(TradeRequest, child_request_id)
            req.updated_at = datetime.utcnow() - timedelta(seconds=10)
            db.commit()
        finally:
            db.close()

        requests_response = self.client.get(f'/api/game/trade-requests/{session_id}/1')
        self.assertEqual(requests_response.status_code, 200)
        items = requests_response.json().get('items', [])
        child_request = next((item for item in items if item['id'] == child_request_id), None)
        self.assertIsNotNone(child_request)
        self.assertIn(child_request['status'], {'COUNTERED', 'REJECTED'})
        self.assertEqual(child_request['parentRequestId'], original_request_id)
        if child_request['status'] == 'COUNTERED':
            self.assertLess(
                int(child_request['items'][0]['proposedPrice']),
                int(counter_trigger_price),
            )
        else:
            self.assertTrue(child_request.get('messageCode'))


if __name__ == '__main__':
    unittest.main()
