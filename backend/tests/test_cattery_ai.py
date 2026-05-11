import unittest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import close_all_sessions, sessionmaker
except Exception:  # pragma: no cover - local env without backend deps
    create_engine = None
    sessionmaker = None

if create_engine is None or sessionmaker is None:  # pragma: no cover
    raise unittest.SkipTest("sqlalchemy is not installed in current python env")

from app import crud
from app.cattery_ai import (
    ARCHETYPES,
    ensure_competitors_for_session,
    evaluate_bankruptcy_plan,
    get_public_spectate_view,
)
from app.db import Base
from app.models import GameSession, Season, User, CatteryCompetitor


class CatteryAITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        cls.Session = sessionmaker(bind=cls.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        close_all_sessions()
        cls.engine.dispose(close=True)

    def setUp(self):
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def _new_user(self) -> User:
        user = User(role="candidate")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_generate_20_bot_catteries_with_archetypes(self):
        user = self._new_user()
        session = GameSession(user_id=user.id, assigned_role="petshop", status="active")
        self.db.add(session)
        self.db.flush()
        self.db.add(
            Season(
                session_id=session.id,
                season_number=1,
                coins_start=40,
                coins_end=40,
                profit=0,
                bot_coins_end=40,
            )
        )
        self.db.commit()

        competitors = ensure_competitors_for_session(self.db, session)
        self.assertEqual(len(competitors), 20)
        bot_rows = [row for row in competitors if row.is_bot]
        self.assertEqual(len(bot_rows), 20)
        self.assertTrue(all(row.archetype in ARCHETYPES for row in bot_rows))
        self.assertGreaterEqual(len(set(row.archetype for row in bot_rows)), 5)

    def test_bankruptcy_plan_triggers_aggressive_sale(self):
        plan = evaluate_bankruptcy_plan(
            coins=1,
            kitten_count=24,
            house_count=2,
            reserve_coins_target=4,
            archetype="BALANCER",
        )
        self.assertTrue(plan.aggressive_sale)
        self.assertGreaterEqual(plan.sell_ratio, 0.7)
        self.assertGreater(plan.urgency_discount, 0.1)

    def test_spectate_public_only_and_trade_forbidden(self):
        user = self._new_user()
        session = crud.start_game_session(self.db, user.id)
        competitors = (
            self.db.query(CatteryCompetitor)
            .filter(CatteryCompetitor.session_id == session.id)
            .order_by(CatteryCompetitor.cattery_id.asc())
            .all()
        )
        self.assertGreaterEqual(len(competitors), 2)
        target_id = 2

        view = get_public_spectate_view(
            self.db,
            session_id=session.id,
            season_number=1,
            cattery_id=target_id,
        )
        self.assertIsNotNone(view)
        self.assertTrue(view["spectateMode"])
        self.assertFalse(view["tradeAllowed"])
        self.assertIn("showcase", view)
        # private fields must not leak
        self.assertNotIn("coins", view)
        self.assertNotIn("state_json", view)

        ok, err = crud.trade_market(
            self.db,
            session=session,
            season_number=1,
            action="buy",
            cat_type="gray",
            qty=1,
            cat_sex="M",
            counterparty_type="cattery",
            counterparty_id=target_id,
        )
        self.assertFalse(ok)
        self.assertEqual(err, "invalid_counterparty_for_role")


if __name__ == "__main__":
    unittest.main()
