from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from .game_config import (
    ADULT_AGE,
    ARCHETYPE_DISTRIBUTION,
    CONFIG_MATCH_CATTERIES,
    CONFIG_START_COINS,
    CONFIG_START_HOUSES,
    CONFIG_START_KITTENS,
    CONFIG_START_PRODUCTION_MODE,
)
from .models import CatteryCompetitor, GameSession


CAT_TYPES = ("black", "white", "gray", "ginger")
CAT_SEXES = ("M", "F")
ARCHETYPES = ("SCALPER", "FARMER", "BALANCER", "RISK_MANAGER", "HIGH_ROLLER")

BASE_PRICES = {
    "black": 23,
    "white": 11,
    "gray": 28,
    "ginger": 34,
}

ARCHETYPE_PRICE_BONUS = {
    "SCALPER": -0.10,
    "FARMER": 0.05,
    "BALANCER": 0.0,
    "RISK_MANAGER": -0.03,
    "HIGH_ROLLER": 0.15,
}

ARCHETYPE_KEEP_RATIO = {
    "SCALPER": 0.20,
    "FARMER": 0.72,
    "BALANCER": 0.48,
    "RISK_MANAGER": 0.42,
    "HIGH_ROLLER": 0.35,
}


@dataclass(frozen=True)
class BankruptcyPlan:
    aggressive_sale: bool
    expected_costs_next_season: int
    reserve_coins_target: int
    urgency_discount: float
    sell_ratio: float


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def assign_archetypes(bot_count: int, seed: str) -> list[str]:
    bot_count = max(0, int(bot_count))
    pool: list[str] = []
    for archetype, count in ARCHETYPE_DISTRIBUTION.items():
        pool.extend([archetype] * max(0, int(count)))
    if not pool:
        pool = ["BALANCER"]

    rnd = random.Random(seed)
    rnd.shuffle(pool)
    out: list[str] = []
    idx = 0
    while len(out) < bot_count:
        out.append(pool[idx % len(pool)])
        idx += 1
    return out


def evaluate_bankruptcy_plan(
    *,
    coins: int,
    kitten_count: int,
    house_count: int,
    reserve_coins_target: int,
    archetype: str,
) -> BankruptcyPlan:
    expected_feed = max(0, int(round(kitten_count * 0.35)))
    expected_treat = max(0, int(round(kitten_count * 0.12))) * 2
    expected_utility = max(1, house_count) * 3
    expected_costs = expected_feed + expected_treat + expected_utility
    min_safe = expected_costs + reserve_coins_target
    aggressive = coins < min_safe
    base_sell_ratio = 1.0 - ARCHETYPE_KEEP_RATIO.get(archetype, 0.48)
    sell_ratio = base_sell_ratio + (0.32 if aggressive else 0.0)
    urgency_discount = 0.18 if aggressive else 0.04
    return BankruptcyPlan(
        aggressive_sale=aggressive,
        expected_costs_next_season=expected_costs,
        reserve_coins_target=reserve_coins_target,
        urgency_discount=_clamp(urgency_discount, 0.0, 0.35),
        sell_ratio=_clamp(sell_ratio, 0.05, 0.95),
    )


def _empty_counts() -> dict[str, dict[str, int]]:
    return {color: {sex: 0 for sex in CAT_SEXES} for color in CAT_TYPES}


def _normalize_state(raw_state_json: str) -> dict[str, Any]:
    try:
        raw = json.loads(raw_state_json or "{}")
    except Exception:
        raw = {}
    counts = _empty_counts()
    source_counts = raw.get("kittens") if isinstance(raw, dict) else None
    if isinstance(source_counts, dict):
        for color in CAT_TYPES:
            sex_map = source_counts.get(color, {})
            if isinstance(sex_map, dict):
                counts[color]["M"] = max(0, _safe_int(sex_map.get("M"), 0))
                counts[color]["F"] = max(0, _safe_int(sex_map.get("F"), 0))
    return {
        "kittens": counts,
        "demandSignal": {
            color: float((raw.get("demandSignal") or {}).get(color, 0.0)) if isinstance(raw, dict) else 0.0
            for color in CAT_TYPES
        },
    }


def _serialize_state(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False)


def _total_kittens(counts: dict[str, dict[str, int]]) -> int:
    return int(sum(counts[color][sex] for color in CAT_TYPES for sex in CAT_SEXES))


def _has_breeding_pair(counts: dict[str, dict[str, int]]) -> bool:
    return any(counts[color]["M"] > 0 and counts[color]["F"] > 0 for color in CAT_TYPES)


def _buy_starter_pair_from_shop(counts: dict[str, dict[str, int]], rnd: random.Random) -> None:
    color = rnd.choice(list(CAT_TYPES))
    counts[color]["M"] += 1
    counts[color]["F"] += 1


def _add_born_kittens(counts: dict[str, dict[str, int]], births: int, rnd: random.Random) -> None:
    for _ in range(max(0, births)):
        color = rnd.choice(list(CAT_TYPES))
        sex = rnd.choice(list(CAT_SEXES))
        counts[color][sex] += 1


def _build_public_catalog(
    counts: dict[str, dict[str, int]],
    *,
    archetype: str,
    urgency_discount: float,
    sell_ratio: float,
    demand_signal: dict[str, float],
    rnd: random.Random,
) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for color in CAT_TYPES:
        color_total = counts[color]["M"] + counts[color]["F"]
        scarcity_factor = _clamp((6 - min(6, color_total)) * 0.035, 0.0, 0.21)
        demand = _clamp(demand_signal.get(color, 0.0), -0.10, 0.25)
        archetype_bonus = ARCHETYPE_PRICE_BONUS.get(archetype, 0.0)
        for sex in CAT_SEXES:
            qty = counts[color][sex]
            listed_qty = max(0, int(round(qty * sell_ratio)))
            if listed_qty <= 0:
                continue
            base_price = BASE_PRICES[color]
            jitter = rnd.uniform(-0.03, 0.03)
            multiplier = 1.0 + scarcity_factor + demand + archetype_bonus + jitter - urgency_discount
            unit_price = max(1, int(round(base_price * _clamp(multiplier, 0.45, 2.10))))
            catalog.append(
                {
                    "catTypeId": color,
                    "catSex": sex,
                    "quantity": listed_qty,
                    "unitPrice": unit_price,
                    "ageLessThan": ADULT_AGE,
                }
            )
    return catalog


def _simulate_single_bot(comp: CatteryCompetitor, season_number: int) -> None:
    if not comp.is_bot:
        comp.season_number = season_number
        comp.public_catalog_json = "[]"
        comp.deals_this_season = 0
        comp.avg_sell_price_this_season = 0.0
        comp.last_deal_at = None
        return

    rnd = random.Random(f"{comp.session_id}:{comp.cattery_id}:{season_number}:{comp.archetype}")
    state = _normalize_state(comp.state_json)
    counts = state["kittens"]

    if season_number == 1 and CONFIG_START_KITTENS > 0:
        for _ in range(CONFIG_START_KITTENS):
            counts[rnd.choice(list(CAT_TYPES))][rnd.choice(list(CAT_SEXES))] += 1

    if not _has_breeding_pair(counts):
        if CONFIG_START_PRODUCTION_MODE == "STARTER_PACK":
            _buy_starter_pair_from_shop(counts, rnd)
        else:
            # BUY_FROM_ZOOSHOP: bot buys pair when possible
            pair_cost = 16
            if comp.coins >= pair_cost:
                comp.coins -= pair_cost
                _buy_starter_pair_from_shop(counts, rnd)

    # breeding output
    pair_count = sum(1 for color in CAT_TYPES if counts[color]["M"] > 0 and counts[color]["F"] > 0)
    births_base = pair_count * (2 if comp.archetype in {"SCALPER", "RISK_MANAGER"} else 3)
    births_jitter = rnd.randint(0, max(0, pair_count))
    _add_born_kittens(counts, births_base + births_jitter, rnd)

    reserve_target = max(2, min(4, _safe_int(comp.reserve_coins_target, 3)))
    plan = evaluate_bankruptcy_plan(
        coins=comp.coins,
        kitten_count=_total_kittens(counts),
        house_count=max(1, _safe_int(comp.houses, 1)),
        reserve_coins_target=reserve_target,
        archetype=comp.archetype,
    )

    # demand signal evolves by season
    for color in CAT_TYPES:
        current = float(state["demandSignal"].get(color, 0.0))
        drift = rnd.uniform(-0.05, 0.07)
        state["demandSignal"][color] = _clamp(current + drift, -0.10, 0.25)

    catalog = _build_public_catalog(
        counts,
        archetype=comp.archetype,
        urgency_discount=plan.urgency_discount,
        sell_ratio=plan.sell_ratio,
        demand_signal=state["demandSignal"],
        rnd=rnd,
    )

    listed_qty = sum(int(item["quantity"]) for item in catalog)
    if listed_qty > 0:
        deals = rnd.randint(max(1, listed_qty // 8), max(1, listed_qty // 3))
        deals = max(0, min(deals, listed_qty))
    else:
        deals = 0
    weighted_sum = sum(item["quantity"] * item["unitPrice"] for item in catalog)
    listed_total_qty = max(1, sum(item["quantity"] for item in catalog))
    avg_price = weighted_sum / listed_total_qty if catalog else 0.0

    # economy impact for bot coins
    income = int(round(deals * (avg_price if avg_price > 0 else rnd.randint(10, 24))))
    costs = plan.expected_costs_next_season
    comp.coins = max(0, comp.coins + income - costs)
    comp.houses = max(0, _safe_int(comp.houses, CONFIG_START_HOUSES))

    comp.state_json = _serialize_state(state)
    comp.public_catalog_json = json.dumps(catalog, ensure_ascii=False)
    comp.deals_this_season = deals
    comp.avg_sell_price_this_season = float(round(avg_price, 2))
    comp.last_deal_at = (
        datetime.utcnow() - timedelta(seconds=rnd.randint(5, 240))
        if deals > 0
        else None
    )
    comp.season_number = season_number


def ensure_competitors_for_session(db: Session, session: GameSession) -> list[CatteryCompetitor]:
    existing = (
        db.query(CatteryCompetitor)
        .filter(CatteryCompetitor.session_id == session.id)
        .order_by(CatteryCompetitor.cattery_id.asc())
        .all()
    )
    if existing:
        return existing

    total = max(1, CONFIG_MATCH_CATTERIES)
    player_cattery_id = 1 if session.assigned_role == "cattery" else None
    bot_slots = total - (1 if player_cattery_id else 0)
    archetypes = assign_archetypes(bot_slots, seed=f"arch:{session.id}")

    created: list[CatteryCompetitor] = []
    bot_idx = 0
    for cattery_id in range(1, total + 1):
        is_player = player_cattery_id == cattery_id
        archetype = "PLAYER" if is_player else archetypes[bot_idx]
        if not is_player:
            bot_idx += 1
        comp = CatteryCompetitor(
            session_id=session.id,
            cattery_id=cattery_id,
            is_player=is_player,
            is_bot=not is_player,
            archetype=archetype,
            coins=CONFIG_START_COINS,
            houses=CONFIG_START_HOUSES,
            reserve_coins_target=3 if archetype == "BALANCER" else random.randint(2, 4),
            state_json=json.dumps({"kittens": _empty_counts(), "demandSignal": {c: 0.0 for c in CAT_TYPES}}, ensure_ascii=False),
            public_catalog_json="[]",
            season_number=1,
        )
        _simulate_single_bot(comp, season_number=1)
        db.add(comp)
        created.append(comp)

    db.flush()
    return created


def advance_competitors_for_season(db: Session, session_id: str, season_number: int) -> None:
    season_number = max(1, int(season_number))
    comps = (
        db.query(CatteryCompetitor)
        .filter(CatteryCompetitor.session_id == session_id)
        .order_by(CatteryCompetitor.cattery_id.asc())
        .all()
    )
    for comp in comps:
        if comp.season_number >= season_number:
            continue
        for step in range(comp.season_number + 1, season_number + 1):
            _simulate_single_bot(comp, season_number=step)
        comp.updated_at = datetime.utcnow()
    db.flush()


def get_public_spectate_view(
    db: Session,
    *,
    session_id: str,
    season_number: int,
    cattery_id: int,
) -> dict[str, Any] | None:
    comp = (
        db.query(CatteryCompetitor)
        .filter(
            CatteryCompetitor.session_id == session_id,
            CatteryCompetitor.cattery_id == cattery_id,
        )
        .one_or_none()
    )
    if not comp:
        return None

    if comp.season_number < season_number:
        advance_competitors_for_season(db, session_id, season_number)
        db.refresh(comp)

    try:
        catalog = json.loads(comp.public_catalog_json or "[]")
        if not isinstance(catalog, list):
            catalog = []
    except Exception:
        catalog = []

    now = datetime.utcnow()
    last_deal_seconds = None
    if comp.last_deal_at:
        last_deal_seconds = max(0, int((now - comp.last_deal_at).total_seconds()))

    return {
        "catteryId": comp.cattery_id,
        "seasonNumber": season_number,
        "spectateMode": True,
        "tradeAllowed": False,
        "message": "Торговля между питомниками недоступна. Вы можете только наблюдать.",
        "showcase": catalog,
        "dealsThisSeason": int(comp.deals_this_season or 0),
        "lastDealSecondsAgo": last_deal_seconds,
        "avgSellPriceThisSeason": float(comp.avg_sell_price_this_season or 0.0),
    }

