import logging
import random
import unittest

from app.trade_bot import (
    ShopBotState,
    botBuildCounterOffer,
    bot_display_buy_price,
    bot_fair_buy_price,
    bot_pricing_snapshot,
    botEvaluateOffer,
    decide_on_offer,
    update_relation,
)


def make_bot_state(**overrides):
    base = ShopBotState(
        botId="shop:2",
        cash=120,
        relationScoreToPlayer=4,
        inventoryByType={"gray": 1, "black": 2, "white": 1, "ginger": 0},
        currentDemandByType={"gray": 0, "black": 0, "white": 1, "ginger": -1},
        expectedResaleValueByType={"gray": 16, "black": 14, "white": 12, "ginger": 8},
        recentAcceptedPricesByType={"gray": [10, 12], "black": [8]},
        pendingRequestsCount=0,
        archetype="MARKET",
    )
    return ShopBotState(**{**base.__dict__, **overrides})


def sell_offer(price: int, *, cat_type: str = "gray") -> dict[str, str | int]:
    return {"catType": cat_type, "proposedPrice": price, "side": "SELL"}


class TradeBotTests(unittest.TestCase):
    def test_display_buy_price_is_close_to_fair_buy_price(self):
        state = make_bot_state()
        snapshot = bot_pricing_snapshot(state, "gray")
        fair_price = int(snapshot["fairBuyPrice"])
        display_price = int(snapshot["displayBuyPrice"])

        self.assertEqual(fair_price, bot_fair_buy_price(state, "gray"))
        self.assertEqual(display_price, bot_display_buy_price(state, "gray"))
        self.assertGreater(fair_price, 0)
        self.assertGreater(display_price, 0)
        self.assertLessEqual(abs(display_price - fair_price), max(1, round(fair_price * 0.08)))

    def test_scenario_1_accepts_good_deal_below_display_price(self):
        state = make_bot_state()
        self.assertEqual(bot_display_buy_price(state, "gray"), 12)

        result = botEvaluateOffer(state, sell_offer(10), rng=random.Random(1))

        self.assertEqual(result.decision, "ACCEPT")
        self.assertEqual(result.reason, "GOOD_DEAL")
        self.assertEqual(result.displayBuyPrice, 12)

    def test_scenario_2_accepts_offer_equal_to_display_price(self):
        state = make_bot_state()

        result = botEvaluateOffer(state, sell_offer(12), rng=random.Random(2))

        self.assertEqual(result.decision, "ACCEPT")
        self.assertIn(result.reason, {"GOOD_DEAL", "FAIR_PRICE"})
        self.assertEqual(result.displayBuyPrice, 12)

    def test_scenario_3_accepts_or_soft_counters_slightly_above_display_price(self):
        state = make_bot_state()

        result = botEvaluateOffer(state, sell_offer(13), rng=random.Random(3))

        self.assertIn(result.decision, {"ACCEPT", "COUNTER"})
        self.assertIn(result.reason, {"BORDERLINE", "FAIR_COUNTER"})
        if result.decision == "COUNTER":
            self.assertIsNotNone(result.counterPrice)
            self.assertLessEqual(result.counterPrice, 13)
            self.assertLessEqual(result.counterPrice, result.displayBuyPrice + 1)

    def test_scenario_4_hard_counter_stays_near_market_price(self):
        state = make_bot_state()

        result = botEvaluateOffer(state, sell_offer(14), rng=random.Random(4))

        self.assertEqual(result.decision, "COUNTER")
        self.assertEqual(result.reason, "FAIR_COUNTER")
        self.assertEqual(result.displayBuyPrice, 12)
        self.assertIsNotNone(result.counterPrice)
        self.assertGreaterEqual(result.counterPrice, 12)
        self.assertLessEqual(result.counterPrice, 13)

    def test_scenario_5_rejects_clearly_overpriced_offer(self):
        result = botEvaluateOffer(make_bot_state(), sell_offer(16), rng=random.Random(5))

        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "PRICE_TOO_HIGH")

    def test_scenario_6_accepts_fallback_very_cheap_offer(self):
        state = make_bot_state(expectedResaleValueByType={"gray": 14, "black": 14, "white": 12, "ginger": 8})

        result = botEvaluateOffer(state, sell_offer(6), rng=random.Random(6))

        self.assertEqual(result.decision, "ACCEPT")
        self.assertEqual(result.reason, "GOOD_DEAL")
        self.assertEqual(result.expectedResaleValue, 14)

    def test_scenario_7_rejects_when_bot_has_low_cash(self):
        result = botEvaluateOffer(make_bot_state(cash=11), sell_offer(12), rng=random.Random(7))

        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "LOW_CASH")

    def test_scenario_8_overstocked_offer_counters_or_rejects(self):
        state = make_bot_state(inventoryByType={"gray": 7, "black": 2, "white": 1, "ginger": 0})

        result = botEvaluateOffer(state, sell_offer(13), rng=random.Random(8))

        self.assertIn(result.decision, {"COUNTER", "REJECT"})
        self.assertEqual(result.reason, "OVERSTOCKED")
        if result.counterPrice is not None:
            self.assertLessEqual(result.counterPrice, result.displayBuyPrice + 1)

    def test_scenario_9_low_demand_offer_counters_or_rejects(self):
        state = make_bot_state(currentDemandByType={"gray": -2, "black": 0, "white": 1, "ginger": -1})

        result = botEvaluateOffer(state, sell_offer(11), rng=random.Random(9))

        self.assertIn(result.decision, {"COUNTER", "REJECT"})
        self.assertEqual(result.reason, "LOW_DEMAND")

    def test_scenario_10_rejects_when_relation_is_zero(self):
        result = botEvaluateOffer(make_bot_state(relationScoreToPlayer=0), sell_offer(6), rng=random.Random(10))

        self.assertEqual(result.decision, "REJECT")
        self.assertEqual(result.reason, "NO_RELATION")

    def test_scenario_11_aggressive_bot_accepts_same_price_more_often(self):
        aggressive = botEvaluateOffer(
            make_bot_state(botId="shop:3", archetype="AGGRESSIVE"),
            sell_offer(12),
            rng=random.Random(11),
        )
        cautious = botEvaluateOffer(
            make_bot_state(botId="shop:1", archetype="CAUTIOUS"),
            sell_offer(12),
            rng=random.Random(11),
        )

        self.assertEqual(aggressive.decision, "ACCEPT")
        self.assertIn(cautious.decision, {"COUNTER", "REJECT"})

    def test_scenario_12_cautious_bot_with_weaker_relation_does_not_auto_accept(self):
        result = botEvaluateOffer(
            make_bot_state(botId="shop:1", archetype="CAUTIOUS", relationScoreToPlayer=2),
            sell_offer(11),
            rng=random.Random(12),
        )

        self.assertIn(result.decision, {"COUNTER", "REJECT"})
        self.assertNotEqual(result.decision, "ACCEPT")

    def test_scenario_13_counter_never_jumps_far_above_display_price(self):
        state = make_bot_state()
        display_price = bot_display_buy_price(state, "gray")

        counter = botBuildCounterOffer(
            sell_offer(14),
            fair_buy_price=bot_fair_buy_price(state, "gray"),
            display_buy_price=display_price,
            min_acceptable_price=int(bot_pricing_snapshot(state, "gray")["minAcceptablePrice"]),
            bot_state=state,
            counter_mode="HARD",
            rng=random.Random(13),
        )

        self.assertGreaterEqual(counter["proposedPrice"], display_price)
        self.assertLessEqual(counter["proposedPrice"], display_price + 1)
        self.assertLess(counter["proposedPrice"], 18)

    def test_scenario_14_price_at_or_below_display_is_not_rejected_without_hard_block(self):
        state = make_bot_state(
            cash=120,
            relationScoreToPlayer=1,
            inventoryByType={"gray": 8, "black": 2, "white": 1, "ginger": 0},
            currentDemandByType={"gray": -2, "black": 0, "white": 1, "ginger": -1},
        )
        display_price = bot_display_buy_price(state, "gray")

        result = botEvaluateOffer(state, sell_offer(display_price), rng=random.Random(14))

        self.assertNotEqual(result.decision, "REJECT")

    def test_ui_price_and_ai_decision_are_consistent(self):
        state = make_bot_state()
        display_price = bot_display_buy_price(state, "gray")
        decision = decide_on_offer([sell_offer(display_price)], state, request_id="req-1", rng=random.Random(15))

        self.assertEqual(decision.action, "ACCEPT")
        self.assertIsNotNone(decision.decision_meta)
        self.assertEqual(decision.decision_meta["lines"][0]["displayBuyPrice"], display_price)
        self.assertEqual(decision.decision_meta["lines"][0]["shopPrice"], display_price)

    def test_decide_on_offer_emits_debug_logging_payload(self):
        state = make_bot_state()

        with self.assertLogs("app.trade_bot", level="DEBUG") as captured:
            decide_on_offer([sell_offer(13)], state, request_id="req-logging", rng=random.Random(16))

        output = "\n".join(captured.output)
        self.assertIn("trade_bot_offer_evaluation", output)
        self.assertIn("req-logging", output)
        self.assertIn("displayBuyPrice", output)
        self.assertIn("fairBuyPrice", output)
        self.assertIn("expectedResaleValue", output)
        self.assertIn("relationScore", output)
        self.assertIn("decision", output)
        self.assertIn("reason", output)

    def test_request_level_counter_contains_counter_items(self):
        decision = decide_on_offer(
            [sell_offer(14), sell_offer(9, cat_type="black")],
            make_bot_state(),
            rng=random.Random(17),
        )

        self.assertEqual(decision.action, "COUNTER")
        self.assertEqual(len(decision.counter_items or []), 2)
        self.assertIsNotNone(decision.decision_meta)
        first_line = decision.decision_meta["lines"][0]
        self.assertLessEqual(first_line["shopPrice"], first_line["displayBuyPrice"] + 1)

    def test_update_relation_penalties_and_bonus(self):
        score = 5.0
        score = update_relation(score, {"type": "price_ok"})
        self.assertGreaterEqual(score, 5.0)

        score = update_relation(score, {"type": "overpriced", "ratio": 0.30})
        self.assertLess(score, 5.1)

        score2 = update_relation(1.0, {"type": "overpriced", "ratio": 0.60})
        self.assertAlmostEqual(score2, 0.0, places=6)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
