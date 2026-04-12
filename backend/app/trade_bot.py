from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from typing import Any

BOT_RESPONSE_DELAY_MS_MIN = 1000
BOT_RESPONSE_DELAY_MS_MAX = 3000
BOT_COUNTER_SELL_MARKUP_MIN = 1.03
BOT_COUNTER_SELL_MARKUP_MAX = 1.10
BOT_BASE_MARGIN_FACTOR = 0.75
DISPLAY_PRICE_MAX_DEVIATION = 0.08
BOT_ZONE2_MULTIPLIER = 1.15
BOT_ZONE3_MULTIPLIER = 1.30

BOT_ARCHETYPE_SETTINGS: dict[str, dict[str, float | int]] = {
    "CAUTIOUS": {
        "baseMarginFactor": 0.70,
        "softAcceptBias": -1.0,
        "softCounterMarkup": 0.00,
        "hardCounterMarkup": 0.00,
        "hardOverstockThreshold": 8,
    },
    "MARKET": {
        "baseMarginFactor": BOT_BASE_MARGIN_FACTOR,
        "softAcceptBias": 0.0,
        "softCounterMarkup": 0.02,
        "hardCounterMarkup": 0.04,
        "hardOverstockThreshold": 9,
    },
    "AGGRESSIVE": {
        "baseMarginFactor": 0.80,
        "softAcceptBias": 1.0,
        "softCounterMarkup": 0.04,
        "hardCounterMarkup": 0.08,
        "hardOverstockThreshold": 10,
    },
}

logger = logging.getLogger(__name__)


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


def _coerce_archetype(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in BOT_ARCHETYPE_SETTINGS:
        return normalized
    return "MARKET"


def shop_bot_archetype(bot_id: str) -> str:
    normalized = str(bot_id or "").strip().lower()
    if normalized.startswith("shop:"):
        try:
            shop_id = int(normalized.split(":", 1)[1])
        except Exception:
            shop_id = 0
        mapping = {
            1: "CAUTIOUS",
            2: "MARKET",
            3: "AGGRESSIVE",
            4: "CAUTIOUS",
            5: "MARKET",
        }
        return mapping.get(shop_id, "MARKET")
    if normalized.startswith("cattery:"):
        try:
            cattery_id = int(normalized.split(":", 1)[1])
        except Exception:
            cattery_id = 0
        return ["CAUTIOUS", "MARKET", "AGGRESSIVE"][cattery_id % 3]
    return "MARKET"


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
    archetype: str = "MARKET"


@dataclass(frozen=True)
class BotOfferEvaluationResult:
    decision: str
    displayBuyPrice: int
    fairBuyPrice: int
    expectedResaleValue: int
    minAcceptablePrice: int
    counterPrice: int | None = None
    reason: str = "BORDERLINE"
    counterMode: str | None = None


@dataclass(frozen=True)
class OfferDecision:
    action: str
    message_code: str | None = None
    counter_items: list[dict[str, Any]] | None = None
    reasons: list[str] | None = None
    decision_meta: dict[str, Any] | None = None


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


def _archetype_settings(bot_state: ShopBotState) -> dict[str, float | int]:
    archetype = _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId))
    return BOT_ARCHETYPE_SETTINGS[archetype]


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


def bot_base_margin_factor(bot_state: ShopBotState) -> float:
    return float(_archetype_settings(bot_state)["baseMarginFactor"])


def round_to_nice_value(value: float) -> int:
    if value <= 0:
        return 0
    floor_value = max(1, int(math.floor(value)))
    ceil_value = max(1, int(math.ceil(value)))
    rounded = max(1, int(round(value)))
    candidates = {floor_value, ceil_value, rounded}
    if value >= 10:
        candidates.add(max(1, int(2 * round(value / 2))))
    ranked = sorted(candidates, key=lambda candidate: (abs(candidate - value), abs(candidate - rounded), candidate))
    close_candidates = [
        candidate
        for candidate in ranked
        if abs(candidate - value) <= max(1.0, value * DISPLAY_PRICE_MAX_DEVIATION)
    ]
    if close_candidates:
        return int(close_candidates[0])
    return int(ranked[0])


def bot_pricing_snapshot(bot_state: ShopBotState, cat_type: str) -> dict[str, int | float | str]:
    relation_factor = _relation_factor(bot_state.relationScoreToPlayer)
    expected_resale_value = bot_market_value(bot_state, cat_type)
    demand_factor = bot_demand_factor(bot_state, cat_type)
    saturation_factor = bot_saturation_factor(bot_state, cat_type)
    base_margin_factor = bot_base_margin_factor(bot_state)
    fair_raw = (
        expected_resale_value
        * base_margin_factor
        * demand_factor
        * saturation_factor
        * relation_factor
    )
    fair_buy_price = 0 if relation_factor <= 0 else max(1, int(round(fair_raw)))
    display_buy_price = 0 if fair_buy_price <= 0 else round_to_nice_value(fair_raw)
    min_acceptable_price = 0 if fair_buy_price <= 0 else max(1, int(math.floor(fair_raw * 0.92)))
    return {
        "archetype": _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId)),
        "expectedResaleValue": expected_resale_value,
        "baseMarginFactor": base_margin_factor,
        "demandFactor": demand_factor,
        "saturationFactor": saturation_factor,
        "relationFactor": relation_factor,
        "fairBuyPrice": fair_buy_price,
        "displayBuyPrice": display_buy_price,
        "minAcceptablePrice": min_acceptable_price,
    }


def bot_fair_buy_price(bot_state: ShopBotState, cat_type: str) -> int:
    return int(bot_pricing_snapshot(bot_state, cat_type)["fairBuyPrice"])


def bot_display_buy_price(bot_state: ShopBotState, cat_type: str) -> int:
    return int(bot_pricing_snapshot(bot_state, cat_type)["displayBuyPrice"])


def bot_min_accept_price(bot_state: ShopBotState, cat_type: str) -> int:
    return int(bot_pricing_snapshot(bot_state, cat_type)["minAcceptablePrice"])


def _price_limit(base_price: int, multiplier: float) -> int:
    if base_price <= 0:
        return 0
    return max(1, int(math.floor(base_price * multiplier)))


def _hard_overstock_block(bot_state: ShopBotState, cat_type: str) -> bool:
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    threshold = int(_archetype_settings(bot_state)["hardOverstockThreshold"])
    return stock >= threshold


def _soft_accept_score(bot_state: ShopBotState, cat_type: str) -> float:
    settings = _archetype_settings(bot_state)
    relation_score = float(_relation_bucket(bot_state.relationScoreToPlayer))
    demand = float(bot_state.currentDemandByType.get(cat_type, 0))
    stock = float(bot_state.inventoryByType.get(cat_type, 0))
    return relation_score + demand - max(0.0, stock - 3.0) * 0.4 + float(settings["softAcceptBias"])


def _counter_reason(bot_state: ShopBotState, cat_type: str, relation_score: int) -> str:
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))
    if stock >= 6:
        return "OVERSTOCKED"
    if demand <= -2:
        return "LOW_DEMAND"
    if relation_score <= 1:
        return "BAD_RELATION"
    return "FAIR_COUNTER"


def _sell_hard_block_reason(bot_state: ShopBotState, cat_type: str) -> str | None:
    return None


def _zone2_should_accept(
    bot_state: ShopBotState,
    cat_type: str,
    *,
    relation_score: int,
) -> bool:
    archetype = _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))

    if archetype == "AGGRESSIVE":
        return relation_score >= 1 and demand >= -1 and stock <= 7
    if archetype == "MARKET":
        return relation_score >= 2 and demand >= -1 and stock <= 5
    return relation_score >= 4 and demand >= 1 and stock <= 3


def _zone3_should_accept(
    bot_state: ShopBotState,
    cat_type: str,
    *,
    relation_score: int,
) -> bool:
    archetype = _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    return archetype == "AGGRESSIVE" and relation_score >= 3 and demand >= 2 and stock <= 2


def _should_reject_zone3(
    bot_state: ShopBotState,
    cat_type: str,
    *,
    relation_score: int,
) -> bool:
    archetype = _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))

    if _hard_overstock_block(bot_state, cat_type) or demand <= -2:
        return True
    if archetype == "CAUTIOUS" and relation_score <= 1:
        return True
    return False


def bot_counter_buy_price(
    bot_state: ShopBotState,
    cat_type: str,
    proposed_price: int,
    *,
    fair_buy_price: int,
    display_buy_price: int,
    min_acceptable_price: int,
    counter_mode: str = "SOFT",
) -> int:
    normalized_mode = str(counter_mode or "SOFT").upper()
    display_anchor = max(1, int(display_buy_price))
    fair_anchor = max(1, int(fair_buy_price or display_anchor))
    floor_price = max(1, max(int(min_acceptable_price or 1), min(display_anchor, fair_anchor)))

    if normalized_mode == "SOFT":
        ceiling = min(
            proposed_price - 1,
            max(floor_price, round_to_nice_value(display_anchor * 1.05)),
        )
        target = max(floor_price, min(display_anchor, ceiling))
    else:
        ceiling = min(
            proposed_price - 1,
            max(floor_price, round_to_nice_value(display_anchor * 1.10)),
        )
        target = max(
            floor_price,
            min(round_to_nice_value(max(display_anchor, fair_anchor)), ceiling),
        )

    if target >= proposed_price:
        target = max(floor_price, proposed_price - 1)
    return max(1, min(target, proposed_price - 1 if proposed_price > 1 else 1))


def botEvaluateOffer(
    bot_state: ShopBotState,
    item: dict[str, Any],
    *,
    rng: random.Random | None = None,
) -> BotOfferEvaluationResult:
    del rng  # decisions are deterministic for the same market conditions
    cat_type = str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower()
    proposed_price = max(
        0,
        int(item.get("proposedPrice") or item.get("unitPrice") or 0),
    )
    side = str(item.get("side") or "SELL").strip().upper()
    pricing = bot_pricing_snapshot(bot_state, cat_type)
    expected_resale_value = int(pricing["expectedResaleValue"])
    display_buy_price = int(pricing["displayBuyPrice"])
    fair_buy_price = int(pricing["fairBuyPrice"])
    min_acceptable_price = int(pricing["minAcceptablePrice"])
    relation_score = _relation_bucket(bot_state.relationScoreToPlayer)
    stock = max(0, int(bot_state.inventoryByType.get(cat_type, 0)))
    demand = int(bot_state.currentDemandByType.get(cat_type, 0))
    zone2_limit = _price_limit(display_buy_price, BOT_ZONE2_MULTIPLIER)
    zone3_limit = _price_limit(display_buy_price, BOT_ZONE3_MULTIPLIER)

    if relation_score == 0:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="NO_RELATION",
        )
    if proposed_price <= 0:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="PRICE_TOO_HIGH" if side == "SELL" else "LOW_DEMAND",
        )

    if side == "BUY":
        min_sell_price = max(
            1,
            int(
                round(
                    expected_resale_value
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
                displayBuyPrice=min_sell_price,
                fairBuyPrice=min_sell_price,
                expectedResaleValue=expected_resale_value,
                minAcceptablePrice=min_sell_price,
                reason="GOOD_DEAL",
            )
        if proposed_price >= int(min_sell_price * 0.90):
            if _soft_accept_score(bot_state, cat_type) >= 4.5:
                return BotOfferEvaluationResult(
                    decision="ACCEPT",
                    displayBuyPrice=min_sell_price,
                    fairBuyPrice=min_sell_price,
                    expectedResaleValue=expected_resale_value,
                    minAcceptablePrice=min_sell_price,
                    reason="BORDERLINE",
                )
            return BotOfferEvaluationResult(
                decision="COUNTER",
                displayBuyPrice=min_sell_price,
                fairBuyPrice=min_sell_price,
                expectedResaleValue=expected_resale_value,
                minAcceptablePrice=min_sell_price,
                counterPrice=max(min_sell_price, proposed_price),
                reason="FAIR_COUNTER",
                counterMode="SOFT",
            )
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=min_sell_price,
            fairBuyPrice=min_sell_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_sell_price,
            reason="PRICE_TOO_HIGH",
        )

    if bot_state.cash < proposed_price:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="LOW_CASH",
        )

    hard_block_reason = _sell_hard_block_reason(bot_state, cat_type)
    if hard_block_reason:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason=hard_block_reason,
        )

    fallback_accept_price = _price_limit(expected_resale_value, 0.5)
    if proposed_price <= fallback_accept_price:
        return BotOfferEvaluationResult(
            decision="ACCEPT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="GOOD_DEAL",
        )

    if proposed_price <= display_buy_price:
        return BotOfferEvaluationResult(
            decision="ACCEPT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="GOOD_DEAL" if proposed_price < display_buy_price else "FAIR_PRICE",
        )

    if proposed_price <= fair_buy_price:
        return BotOfferEvaluationResult(
            decision="ACCEPT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="FAIR_PRICE",
        )

    if proposed_price <= zone2_limit:
        if _zone2_should_accept(bot_state, cat_type, relation_score=relation_score):
            return BotOfferEvaluationResult(
                decision="ACCEPT",
                displayBuyPrice=display_buy_price,
                fairBuyPrice=fair_buy_price,
                expectedResaleValue=expected_resale_value,
                minAcceptablePrice=min_acceptable_price,
                reason="FAIR_PRICE" if proposed_price <= fair_buy_price else "ABOVE_MARKET_BUT_ACCEPTABLE",
            )
        reason = _counter_reason(bot_state, cat_type, relation_score)
        return BotOfferEvaluationResult(
            decision="COUNTER",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            counterPrice=bot_counter_buy_price(
                bot_state,
                cat_type,
                proposed_price,
                fair_buy_price=fair_buy_price,
                display_buy_price=display_buy_price,
                min_acceptable_price=min_acceptable_price,
                counter_mode="SOFT",
            ),
            reason=reason,
            counterMode="SOFT",
        )

    if proposed_price <= zone3_limit:
        reason = _counter_reason(bot_state, cat_type, relation_score)
        if _zone3_should_accept(bot_state, cat_type, relation_score=relation_score):
            return BotOfferEvaluationResult(
                decision="ACCEPT",
                displayBuyPrice=display_buy_price,
                fairBuyPrice=fair_buy_price,
                expectedResaleValue=expected_resale_value,
                minAcceptablePrice=min_acceptable_price,
                reason="ABOVE_MARKET_BUT_ACCEPTABLE",
            )
        if _should_reject_zone3(bot_state, cat_type, relation_score=relation_score):
            return BotOfferEvaluationResult(
                decision="REJECT",
                displayBuyPrice=display_buy_price,
                fairBuyPrice=fair_buy_price,
                expectedResaleValue=expected_resale_value,
                minAcceptablePrice=min_acceptable_price,
                reason=reason,
            )
        return BotOfferEvaluationResult(
            decision="COUNTER",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            counterPrice=bot_counter_buy_price(
                bot_state,
                cat_type,
                proposed_price,
                fair_buy_price=fair_buy_price,
                display_buy_price=display_buy_price,
                min_acceptable_price=min_acceptable_price,
                counter_mode="HARD",
            ),
            reason=reason,
            counterMode="HARD",
        )

    if demand <= -2:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="LOW_DEMAND",
        )
    if max(0, int(bot_state.inventoryByType.get(cat_type, 0))) >= 6:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="OVERSTOCKED",
        )
    if relation_score <= 1:
        return BotOfferEvaluationResult(
            decision="REJECT",
            displayBuyPrice=display_buy_price,
            fairBuyPrice=fair_buy_price,
            expectedResaleValue=expected_resale_value,
            minAcceptablePrice=min_acceptable_price,
            reason="BAD_RELATION",
        )
    return BotOfferEvaluationResult(
        decision="REJECT",
        displayBuyPrice=display_buy_price,
        fairBuyPrice=fair_buy_price,
        expectedResaleValue=expected_resale_value,
        minAcceptablePrice=min_acceptable_price,
        reason="PRICE_TOO_HIGH",
    )


def botBuildCounterOffer(
    item: dict[str, Any],
    *,
    fair_buy_price: int,
    display_buy_price: int | None = None,
    min_acceptable_price: int,
    bot_state: ShopBotState | None = None,
    counter_mode: str = "SOFT",
    rng: random.Random | None = None,
) -> dict[str, Any]:
    del rng
    normalized = dict(item)
    proposed_price = max(
        1,
        int(normalized.get("proposedPrice") or normalized.get("unitPrice") or 1),
    )
    side = str(normalized.get("side") or "SELL").strip().upper()
    display_buy_price = max(1, int(display_buy_price or fair_buy_price or proposed_price))

    if side == "BUY":
        raw_counter = int(round(proposed_price * BOT_COUNTER_SELL_MARKUP_MIN))
        counter_price = max(min_acceptable_price, raw_counter, proposed_price)
    else:
        effective_bot_state = bot_state or ShopBotState(
            botId="shop:0",
            cash=proposed_price,
            relationScoreToPlayer=5.0,
            inventoryByType={},
            currentDemandByType={},
            expectedResaleValueByType={},
            recentAcceptedPricesByType={},
            pendingRequestsCount=0,
            archetype="MARKET",
        )
        cat_type = str(normalized.get("catType") or normalized.get("catColor") or normalized.get("catTypeId") or "").strip().lower()
        counter_price = bot_counter_buy_price(
            effective_bot_state,
            cat_type,
            proposed_price,
            fair_buy_price=fair_buy_price,
            display_buy_price=display_buy_price,
            min_acceptable_price=min_acceptable_price,
            counter_mode=counter_mode,
        )

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
        "PRICE_TOO_HIGH": "BOT_TOO_EXPENSIVE",
        "ABOVE_MARKET_BUT_ACCEPTABLE": "BOT_ACCEPTED",
        "GOOD_DEAL": "BOT_REJECTED",
        "FAIR_PRICE": "BOT_REJECTED",
        "FAIR_COUNTER": "BOT_COUNTERED",
    }
    return mapping.get(reason, "BOT_REJECTED")


def _decision_meta_from_evaluations(
    *,
    action: str,
    request_items: list[dict[str, Any]],
    decisions: list[BotOfferEvaluationResult],
    bot_state: ShopBotState,
) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    for item, evaluation in zip(request_items, decisions):
        proposed_price = max(0, int(item.get("proposedPrice") or item.get("unitPrice") or 0))
        if action == "COUNTER":
            shop_price = int(evaluation.counterPrice or evaluation.displayBuyPrice)
        elif action == "ACCEPT":
            shop_price = proposed_price
        else:
            shop_price = int(evaluation.displayBuyPrice)
        lines.append(
            {
                "catType": str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower(),
                "playerPrice": proposed_price,
                "shopPrice": shop_price,
                "displayBuyPrice": int(evaluation.displayBuyPrice),
                "fairBuyPrice": int(evaluation.fairBuyPrice),
                "expectedResaleValue": int(evaluation.expectedResaleValue),
                "counterBuyPrice": int(evaluation.counterPrice or 0),
                "reason": evaluation.reason,
            }
        )
    if action == "COUNTER":
        message = "Магазин готов торговаться, но предлагает цену ближе к своей рыночной оценке."
    elif action == "REJECT":
        message = "Магазин считает текущую цену слишком далекой от рыночной."
    else:
        message = "Магазин одобрил сделку по предложенной цене."
    return {
        "kind": f"BOT_{action}",
        "reason": decisions[0].reason if decisions else None,
        "message": message,
        "botArchetype": _coerce_archetype(bot_state.archetype or shop_bot_archetype(bot_state.botId)),
        "lines": lines,
    }


def decide_on_offer(
    request_items: list[dict[str, Any]],
    bot_state: ShopBotState,
    request_id: str | None = None,
    rng: random.Random | None = None,
) -> OfferDecision:
    if not request_items:
        return OfferDecision(action="REJECT", message_code="EMPTY_ITEMS", reasons=["PRICE_TOO_HIGH"])

    counter_items: list[dict[str, Any]] = []
    decisions: list[BotOfferEvaluationResult] = []
    total_sell_price = 0

    for item in request_items:
        proposed_price = max(0, int(item.get("proposedPrice") or item.get("unitPrice") or 0))
        if str(item.get("side") or "SELL").strip().upper() == "SELL":
            total_sell_price += proposed_price
        evaluation = botEvaluateOffer(bot_state, item, rng=rng)
        decisions.append(evaluation)
        logger.debug(
            "trade_bot_offer_evaluation %s",
            {
                "requestId": request_id,
                "botId": bot_state.botId,
                "catType": str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower(),
                "proposedPrice": proposed_price,
                "displayBuyPrice": evaluation.displayBuyPrice,
                "fairBuyPrice": evaluation.fairBuyPrice,
                "expectedResaleValue": evaluation.expectedResaleValue,
                "demand": int(
                    bot_state.currentDemandByType.get(
                        str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower(),
                        0,
                    )
                ),
                "stock": int(
                    bot_state.inventoryByType.get(
                        str(item.get("catType") or item.get("catColor") or item.get("catTypeId") or "").strip().lower(),
                        0,
                    )
                ),
                "cash": max(0, int(bot_state.cash)),
                "relationScore": float(bot_state.relationScoreToPlayer),
                "decision": evaluation.decision,
                "reason": evaluation.reason,
            },
        )
        if evaluation.decision == "COUNTER":
            counter_items.append(
                botBuildCounterOffer(
                    item,
                    fair_buy_price=evaluation.fairBuyPrice,
                    display_buy_price=evaluation.displayBuyPrice,
                    min_acceptable_price=evaluation.minAcceptablePrice,
                    bot_state=bot_state,
                    counter_mode=evaluation.counterMode or "SOFT",
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
        return OfferDecision(
            action="REJECT",
            message_code="RELATION_ZERO",
            reasons=["NO_RELATION"],
            decision_meta=_decision_meta_from_evaluations(
                action="REJECT",
                request_items=request_items,
                decisions=decisions,
                bot_state=bot_state,
            ),
        )
    if total_sell_price > max(0, int(bot_state.cash)):
        return OfferDecision(
            action="REJECT",
            message_code="BOT_LOW_CASH",
            reasons=["LOW_CASH"],
            decision_meta=_decision_meta_from_evaluations(
                action="REJECT",
                request_items=request_items,
                decisions=decisions,
                bot_state=bot_state,
            ),
        )

    if any(result.decision == "REJECT" for result in decisions):
        reject = next(result for result in decisions if result.decision == "REJECT")
        return OfferDecision(
            action="REJECT",
            message_code=_message_code_for_reason(reject.reason, "REJECT"),
            reasons=[result.reason for result in decisions],
            decision_meta=_decision_meta_from_evaluations(
                action="REJECT",
                request_items=request_items,
                decisions=decisions,
                bot_state=bot_state,
            ),
        )
    if any(result.decision == "COUNTER" for result in decisions):
        return OfferDecision(
            action="COUNTER",
            message_code="BOT_COUNTERED",
            counter_items=counter_items,
            reasons=[result.reason for result in decisions],
            decision_meta=_decision_meta_from_evaluations(
                action="COUNTER",
                request_items=request_items,
                decisions=decisions,
                bot_state=bot_state,
            ),
        )
    return OfferDecision(
        action="ACCEPT",
        message_code="BOT_ACCEPTED",
        reasons=[result.reason for result in decisions],
        decision_meta=_decision_meta_from_evaluations(
            action="ACCEPT",
            request_items=request_items,
            decisions=decisions,
            bot_state=bot_state,
        ),
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
