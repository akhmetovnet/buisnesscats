import random
import unittest

from app.trade_bot import (
    ShopBotState,
    botBuildCounterOffer,
    botEvaluateOffer,
    decide_on_offer,
    update_relation,
)


def make_bot_state(**overrides):
    base = ShopBotState(
        botId="shop:1",
        cash=120,
        relationScoreToPlayer=4,
        inventoryByType={"gray": 1, "black": 2, "white": 1, "ginger": 0},
        currentDemandByType={"gray": 2, "black": 0, "white": 1, "ginger": -1},
        expectedResaleValueByType={"gray": 20, "black": 14, "white": 12, "ginger": 8},
        recentAcceptedPricesByType={"gray": [10, 12], "black": [8]},
        pendingRequestsCount=0,
    )
    return ShopBotState(**{**base.__dict__, **overrides})


class TradeBotTests(unittest.TestCase):
    def test_accept_cheap_offer(self):
        result = botEvaluateOffer(
            make_bot_state(),
            {"catType": "gray", "proposedPrice": 8, "side": "SELL"},
            rng=random.Random(1),
        )
        self.assertEqual(result.decision, "ACCEPT")
        self.assertEqual(result.reason, "GOOD_DEAL")

    def test_counter_borderline_offer(self):
        state = make_bot_state(relationScoreToPlayer=3)
        result = botEvaluateOffer(
            state,
            {"catType": "gray", "proposedPrice": 16, "side": "SELL"},
            rng=random.Random(0),
        )
        self.assertEqual(result.decision, "COUNTER")
        self.assertIsNotNone(result.counterPrice)
        self.assertLessEqual(result.counterPrice, 16)

    def test_reject_too_expensive_offer(self):
        result = botEvaluateOffer(
            make_bot_state(),
            {"catType": "gray", "proposedPrice": 40, "side": "SELL"},
            rng=random.Random(2),
        )
        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "TOO_EXPENSIVE")

    def test_reject_when_relation_zero(self):
        result = botEvaluateOffer(
            make_bot_state(relationScoreToPlayer=0),
            {"catType": "gray", "proposedPrice": 3, "side": "SELL"},
            rng=random.Random(3),
        )
        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "NO_RELATION")

    def test_reject_when_cash_insufficient(self):
        result = botEvaluateOffer(
            make_bot_state(cash=5),
            {"catType": "gray", "proposedPrice": 9, "side": "SELL"},
            rng=random.Random(4),
        )
        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "LOW_CASH")

    def test_relation_score_impacts_decision(self):
        bad_relation = botEvaluateOffer(
            make_bot_state(relationScoreToPlayer=1),
            {"catType": "black", "proposedPrice": 10, "side": "SELL"},
            rng=random.Random(5),
        )
        good_relation = botEvaluateOffer(
            make_bot_state(relationScoreToPlayer=5),
            {"catType": "black", "proposedPrice": 10, "side": "SELL"},
            rng=random.Random(5),
        )
        self.assertNotEqual(bad_relation.decision, good_relation.decision)
        self.assertEqual(good_relation.decision, "ACCEPT")

    def test_build_counter_offer_respects_minimum(self):
        counter = botBuildCounterOffer(
            {"catType": "gray", "proposedPrice": 16, "side": "SELL"},
            fair_buy_price=15,
            min_acceptable_price=13,
            rng=random.Random(6),
        )
        self.assertEqual(counter["quantity"], 1)
        self.assertGreaterEqual(counter["proposedPrice"], 13)
        self.assertLessEqual(counter["proposedPrice"], 16)

    def test_decide_on_offer_returns_request_level_decision(self):
        decision = decide_on_offer(
            [
                {"catType": "gray", "proposedPrice": 20, "side": "SELL"},
                {"catType": "black", "proposedPrice": 9, "side": "SELL"},
            ],
            make_bot_state(),
            rng=random.Random(7),
        )
        self.assertEqual(decision.action, "COUNTER")
        self.assertEqual(len(decision.counter_items or []), 2)

    def test_update_relation_penalties_and_bonus(self):
        score = 5.0
        score = update_relation(score, {"type": "price_ok"})
        self.assertGreaterEqual(score, 5.0)

        score = update_relation(score, {"type": "overpriced", "ratio": 0.30})
        self.assertLess(score, 5.1)

        score2 = update_relation(1.0, {"type": "overpriced", "ratio": 0.60})
        self.assertAlmostEqual(score2, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
