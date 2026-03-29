from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

BOT_RESPONSE_DELAY_MS_MIN = 1000
BOT_RESPONSE_DELAY_MS_MAX = 3000
BOT_COUNTER_DISCOUNT_MIN = 0.90
BOT_COUNTER_DISCOUNT_MAX = 0.97
BOT_COUNTER_SELL_MARKUP_MIN = 1.03
BOT_COUNTER_SELL_MARKUP_MAX = 1.10
BOT_BASE_MARGIN_FACTOR = 0.75


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _clamp_relation(score: float) -> float:
    return _clamp(score, 0.0, 5.0)


def _relation_bucket(score: float) -> int:
    return int(round(_clamp_relation(score)))


def _relation_factor(score: float) -> float:
    bucket = _relation_bucket(score)
    if bucket == 5:
        return 1.05
    if bucket == 4:
        return 1.00
    if bucket == 3:
        return 0.95
    if bucket == 2:
        return 0.90
    if bucket == 1:
        return 0.80
    return 0.0


@dataclass(frozen=True)
class ShopBotState:
    botId: str
    cash: int
    relationScoreToPlayer: float
    inventoryByType: dict[str, int]
    currentDemandByType: dict[str, int]
    expectedResaleValueByType: dict[str, int]
    recentAcceptedPricesByType: dict[str, list[int]]
    pendingRequestsCount: int


@dataclass(frozen=True)
class BotOfferEvaluationResult:
    decision: str
    fairBuyPrice: int
    marketValue: int
    minAcceptablePrice: int
    counterPrice: int | None = None
    reason: str = "BORDERLINE"


@dataclass(frozen=True)
class OfferDecision:
    action: str
    message_code: str | None = None
    counter_items: list[dict[str, Any]] | None = None
    reasons: list[str] | None = None


def update_relation(current_score: float, event: dict[str, Any]) -> float:
    score = _clamp_relation(current_score)
    event_type = str(event.get("type") or "").strip().lower()

    if event_type == "price_ok":
        score += 0.2
    elif event_type == "counter_accepted":
        score += 0.15
    elif event_type == "overpriced":
        ratio = float(event.get("ratio") or 0.0)
        if ratio >= 0.50:
            score -= 1.0
        elif ratio >= 0.25:
            score -= 0.5
        elif ratio >= 0.10:
            score -= 0.25
    elif event_type == "spam":
        extra = max(0, int(event.get("extra", 0)))
        score -= 0.1 * extra
    elif event_type == "cancel":
        score -= 0.1

    return _clamp_relation(score)


def bot_market_value(bot_state: ShopBotState, cat_type: str) -> int:
    return max(1, int(bot_state.expectedResaleValueByType.get(cat_type, 1)))


def bot_demand_factor(bot_state: ShopBotState, cat_type: str) -> float:
    demand = float(bot_state.currentDemandByType.get(cat_type, 0))
    return _clamp(1 + demand * 0.1, 0.8, 1.2)


def bot_saturation_factor(bot_state: ShopBotState, cat_type: str) -> float:
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    if stock == 0:
        return 1.1
    if stock <= 2:
        return 1.0
    if stock <= 4:
        return 0.9
    return 0.75


def bot_fair_buy_price(bot_state: ShopBotState, cat_type: str) -> int:
    relation_factor = _relation_factor(bot_state.relationScoreToPlayer)
    if relation_factor <= 0:
        return 0
    market_value = bot_market_value(bot_state, cat_type)
    demand_factor = bot_demand_factor(bot_state, cat_type)
    saturation_factor = bot_saturation_factor(bot_state, cat_type)
    fair = (
        market_value
        * BOT_BASE_MARGIN_FACTOR
        * demand_factor
        * saturation_factor
        * relation_factor
    )
    return max(1, int(round(fair)))


def bot_min_accept_price(bot_state: ShopBotState, cat_type: str) -> int:
    fair_buy_price = bot_fair_buy_price(bot_state, cat_type)
    if fair_buy_price <= 0:
        return 0
    return max(1, int(fair_buy_price * 0.92))


def botEvaluateOffer(
    bot_state: ShopBotState,
    item: dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> BotOfferEvaluationResult:
    random_gen = rng or random.Random()
    cat_type = str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower()
    proposed_price = max(
        0,
        int(item.get("proposedPrice") or item.get("unitPrice") or 0),
    )
    side = str(item.get("side") or "SELL").strip().upper()
    market_value = bot_market_value(bot_state, cat_type)
    fair_buy_price = bot_fair_buy_price(bot_state, cat_type)
    min_acceptable_price = bot_min_accept_price(bot_state, cat_type)
    relation_score = _relation_bucket(bot_state.relationScoreToPlayer)
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))

    if relation_score == 0:
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="NO_RELATION",
        )
    if proposed_price <= 0:
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="TOO_EXPENSIVE" if side == "SELL" else "LOW_DEMAND",
        )

    if side == "BUY":
        min_sell_price = max(
            1,
            int(
                round(
                    market_value
                    * _clamp(
                        1.08
                        - (_relation_factor(bot_state.relationScoreToPlayer) - 0.8) * 0.15
                        + max(0, stock - 3) * 0.03,
                        0.92,
                        1.20,
                    )
                )
            ),
        )
        if proposed_price >= int(min_sell_price * 1.05):
            return BotOfferEvaluationResult(
                decision="ACCEPT",
                fairBuyPrice=min_sell_price,
                marketValue=market_value,
                minAcceptablePrice=min_sell_price,
                reason="GOOD_DEAL",
            )
        if proposed_price >= int(min_sell_price * 0.9):
            counter_price = max(min_sell_price, proposed_price)
            if random_gen.random() < 0.45:
                return BotOfferEvaluationResult(
                    decision="ACCEPT",
                    fairBuyPrice=min_sell_price,
                    marketValue=market_value,
                    minAcceptablePrice=min_sell_price,
                    reason="BORDERLINE",
                )
            return BotOfferEvaluationResult(
                decision="COUNTER",
                fairBuyPrice=min_sell_price,
                marketValue=market_value,
                minAcceptablePrice=min_sell_price,
                counterPrice=counter_price,
                reason="BORDERLINE",
            )
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=min_sell_price,
            marketValue=market_value,
            minAcceptablePrice=min_sell_price,
            reason="TOO_EXPENSIVE",
        )

    if bot_state.cash < proposed_price:
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="LOW_CASH",
        )
    if demand <= -2:
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="LOW_DEMAND",
        )
    if stock >= 6:
        return BotOfferEvaluationResult(
            decision="REJECT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="OVERSTOCKED",
        )

    if proposed_price <= int(fair_buy_price * 0.9):
        return BotOfferEvaluationResult(
            decision="ACCEPT",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            reason="GOOD_DEAL",
        )
    if proposed_price <= int(fair_buy_price * 1.1):
        if random_gen.random() < 0.55 + (relation_score - 1) * 0.08:
            return BotOfferEvaluationResult(
                decision="ACCEPT",
                fairBuyPrice=fair_buy_price,
                marketValue=market_value,
                minAcceptablePrice=min_acceptable_price,
                reason="BORDERLINE",
            )
        return BotOfferEvaluationResult(
            decision="COUNTER",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            counterPrice=botBuildCounterOffer(item, fair_buy_price, min_acceptable_price, rng=random_gen)["proposedPrice"],
            reason="BORDERLINE",
        )
    if proposed_price <= int(fair_buy_price * 1.25):
        return BotOfferEvaluationResult(
            decision="COUNTER",
            fairBuyPrice=fair_buy_price,
            marketValue=market_value,
            minAcceptablePrice=min_acceptable_price,
            counterPrice=botBuildCounterOffer(item, fair_buy_price, min_acceptable_price, rng=random_gen)["proposedPrice"],
            reason="BORDERLINE",
        )
    return BotOfferEvaluationResult(
        decision="REJECT",
        fairBuyPrice=fair_buy_price,
        marketValue=market_value,
        minAcceptablePrice=min_acceptable_price,
        reason="TOO_EXPENSIVE",
    )


def botBuildCounterOffer(
    item: dict[str, Any],
    fair_buy_price: int,
    min_acceptable_price: int,
    *,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    random_gen = rng or random.Random()
    normalized = dict(item)
    proposed_price = max(
        1,
        int(normalized.get("proposedPrice") or normalized.get("unitPrice") or 1),
    )
    side = str(normalized.get("side") or "SELL").strip().upper()

    if side == "BUY":
        raw_counter = int(round(proposed_price * random_gen.uniform(BOT_COUNTER_SELL_MARKUP_MIN, BOT_COUNTER_SELL_MARKUP_MAX)))
        counter_price = max(min_acceptable_price, raw_counter, proposed_price)
    else:
        raw_counter = int(round(proposed_price * random_gen.uniform(BOT_COUNTER_DISCOUNT_MIN, BOT_COUNTER_DISCOUNT_MAX)))
        counter_price = max(min_acceptable_price, min(proposed_price, raw_counter))
        if counter_price > proposed_price:
            counter_price = proposed_price

    normalized["proposedPrice"] = counter_price
    normalized["unitPrice"] = counter_price
    normalized["quantity"] = 1
    normalized["currency"] = "COIN"
    return normalized


def _message_code_for_reason(reason: str, action: str) -> str:
    if action == "ACCEPT":
        return "BOT_ACCEPTED"
    if action == "COUNTER":
        return "BOT_COUNTERED"
    mapping = {
        "NO_RELATION": "RELATION_ZERO",
        "LOW_CASH": "BOT_LOW_CASH",
        "LOW_DEMAND": "BOT_LOW_DEMAND",
        "OVERSTOCKED": "BOT_OVERSTOCKED",
        "BAD_RELATION": "BOT_BAD_RELATION",
        "TOO_EXPENSIVE": "BOT_TOO_EXPENSIVE",
        "BORDERLINE": "BOT_BORDERLINE_REJECT",
        "GOOD_DEAL": "BOT_REJECTED",
    }
    return mapping.get(reason, "BOT_REJECTED")


def decide_on_offer(
    request_items: list[dict[str, Any]],
    bot_state: ShopBotState,
    rng: random.Random | None = None,
) -> OfferDecision:
    random_gen = rng or random.Random()
    if not request_items:
        return OfferDecision(action="REJECT", message_code="EMPTY_ITEMS", reasons=["TOO_EXPENSIVE"])

    counter_items: list[dict[str, Any]] = []
    decisions: list[BotOfferEvaluationResult] = []
    total_sell_price = 0

    for item in request_items:
        proposed_price = max(0, int(item.get("proposedPrice") or item.get("unitPrice") or 0))
        if str(item.get("side") or "SELL").strip().upper() == "SELL":
            total_sell_price += proposed_price
        evaluation = botEvaluateOffer(bot_state, item, rng=random_gen)
        decisions.append(evaluation)
        if evaluation.decision == "COUNTER":
            counter_items.append(
                botBuildCounterOffer(
                    item,
                    fair_buy_price=evaluation.fairBuyPrice,
                    min_acceptable_price=evaluation.minAcceptablePrice,
                    rng=random_gen,
                )
            )
        else:
            passthrough = dict(item)
            passthrough["proposedPrice"] = max(1, proposed_price)
            passthrough["unitPrice"] = max(1, proposed_price)
            passthrough["quantity"] = 1
            passthrough["currency"] = "COIN"
            counter_items.append(passthrough)

    if _relation_bucket(bot_state.relationScoreToPlayer) == 0:
        return OfferDecision(action="REJECT", message_code="RELATION_ZERO", reasons=["NO_RELATION"])
    if total_sell_price > max(0, int(bot_state.cash)):
        return OfferDecision(action="REJECT", message_code="BOT_LOW_CASH", reasons=["LOW_CASH"])

    if any(result.decision == "REJECT" for result in decisions):
        reject = next(result for result in decisions if result.decision == "REJECT")
        return OfferDecision(
            action="REJECT",
            message_code=_message_code_for_reason(reject.reason, "REJECT"),
            reasons=[result.reason for result in decisions],
        )
    if any(result.decision == "COUNTER" for result in decisions):
        return OfferDecision(
            action="COUNTER",
            message_code="BOT_COUNTERED",
            counter_items=counter_items,
            reasons=[result.reason for result in decisions],
        )
    return OfferDecision(
        action="ACCEPT",
        message_code="BOT_ACCEPTED",
        reasons=[result.reason for result in decisions],
    )


def relation_margin_target(score: float) -> float:
    relation_factor = _relation_factor(score)
    if relation_factor <= 0:
        return 0.0
    return BOT_BASE_MARGIN_FACTOR * relation_factor


def fair_buy_price(market_sell_price: float, relation_score: float) -> float:
    relation_factor = _relation_factor(relation_score)
    if relation_factor <= 0:
        return 0.0
    return max(0.0, float(market_sell_price) * BOT_BASE_MARGIN_FACTOR * relation_factor)


updateRelation = update_relation
decideOnOffer = decide_on_offer
buildCounterOffer = botBuildCounterOffer
