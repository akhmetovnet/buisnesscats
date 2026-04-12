from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from . import crud
from .game_config import ADULT_AGE
from .models import GameEvent, GameSession, TradeBotState, TradeRelation, TradeRequest
from .trade_bot import (
    BOT_RESPONSE_DELAY_MS_MAX,
    BOT_RESPONSE_DELAY_MS_MIN,
    OfferDecision,
    ShopBotState,
    bot_display_buy_price,
    decide_on_offer,
    shop_bot_archetype,
    update_relation,
)
from .trade_state_machine import (
    TradeAction,
    TradeState,
    can_transition,
    is_terminal,
    transition_state,
)


UI_CATEGORY_ICON: dict[str, str] = {
    "OUTGOING": "/assets/ischodychayazayavka.png",
    "INCOMING": "/assets/incoming_equest.png",
    "REJECTED_BY_OTHER": "/assets/REJECTED_APPLICATION_anotherplayer.png",
    "ACCEPTED_BY_OTHER": "/assets/ACCEPTEDAPPLICATIONBYANOTHERPLAYER.png",
    "COUNTER": "/assets/COUNTER-REQUEST.png",
    "REQUIRES_CLARIFICATION": "/assets/APPLICATIONREQUIRINGCLARIFICATION.png",
    "WAITING_FOR_CLARIFICATION": "/assets/APPLICATIONFORCLARIFICATIONFROMANOTHERPLAYER.png",
}

BOT_SHOP_NAMES: dict[int, str] = {
    1: "Бонифаций",
    2: "Полосатый",
    3: "Любимец",
    4: "Мурзик",
    5: "Зооцентр",
}

OPEN_STATES = {TradeState.PENDING, TradeState.COUNTERED, TradeState.NEEDS_CLARIFICATION, TradeState.AWAITING_CLARIFICATION}
SELLER_SIDE = "SELL"
BUYER_SIDE = "BUY"


def user_player_id(user_id: str) -> str:
    return f"user:{user_id}"


def counterparty_player_id(counterparty_type: str, counterparty_id: int) -> str:
    return f"{counterparty_type}:{int(counterparty_id)}"


def is_user_player(player_id: str) -> bool:
    return isinstance(player_id, str) and player_id.startswith("user:")


def bot_response_delay_seconds(rng: random.Random | None = None) -> float:
    random_gen = rng or random.Random()
    delay_ms = random_gen.randint(BOT_RESPONSE_DELAY_MS_MIN, BOT_RESPONSE_DELAY_MS_MAX)
    return delay_ms / 1000.0


def bot_response_delay_seconds_for_request(request_id: str) -> float:
    return bot_response_delay_seconds(rng=random.Random(f"bot-delay:{request_id}"))


def _other_party(req: TradeRequest, actor_player_id: str) -> str:
    return req.to_player_id if actor_player_id == req.from_player_id else req.from_player_id


def _parse_bot_player(player_id: str) -> tuple[str, int] | None:
    if not isinstance(player_id, str) or ":" not in player_id:
        return None
    cp_type, cp_id = player_id.split(":", 1)
    cp_type = cp_type.strip().lower()
    if cp_type not in {"shop", "cattery"}:
        return None
    try:
        return cp_type, int(cp_id)
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _norm_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized == "orange":
        normalized = "ginger"
    return normalized if normalized in {"black", "white", "gray", "ginger"} else None


def _norm_sex(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {"M", "F"} else None


def _norm_side(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {BUYER_SIDE, SELLER_SIDE} else None


def _default_bot_inventory_json() -> str:
    counts = {
        color: {"M": 6, "F": 6}
        for color in ["black", "white", "gray", "ginger"]
    }
    return json.dumps({"counts": counts, "entities": []}, ensure_ascii=False)


def _make_item_id(cat_id: str | None = None) -> str:
    suffix = uuid.uuid4().hex[:10]
    if cat_id:
        return f"item-{cat_id}-{suffix}"
    return f"item-{suffix}"


def _normalize_item(raw_item: dict[str, Any], *, index: int = 0, legacy_part: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw_item, dict):
        return None
    color = _norm_color(
        raw_item.get("catType")
        or raw_item.get("catColor")
        or raw_item.get("catTypeId")
        or raw_item.get("color")
    )
    side = _norm_side(raw_item.get("side"))
    if color is None or side is None:
        return None

    sex = _norm_sex(raw_item.get("catSex") or raw_item.get("sex"))
    proposed_price = max(
        1,
        _safe_int(raw_item.get("proposedPrice") or raw_item.get("unitPrice"), 1),
    )
    cat_id = str(
        raw_item.get("catId")
        or raw_item.get("entityId")
        or f"legacy-{color}-{sex or 'X'}-{index}-{legacy_part}"
    )
    item_id = str(raw_item.get("itemId") or _make_item_id(cat_id))
    return {
        "itemId": item_id,
        "catId": cat_id,
        "catType": color,
        "catColor": color,
        "catTypeId": color,
        "catSex": sex,
        "proposedPrice": proposed_price,
        "unitPrice": proposed_price,
        "quantity": 1,
        "currency": "COIN",
        "side": side,
    }


def _parse_items(items_json: str | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if isinstance(items_json, list):
        raw = items_json
    else:
        try:
            raw = json.loads(items_json or "[]")
        except Exception:
            raw = []
    if not isinstance(raw, list):
        return []

    items: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        raw_qty = max(1, _safe_int(item.get("quantity"), 1))
        for part in range(raw_qty):
            normalized = _normalize_item(item, index=idx, legacy_part=part)
            if normalized:
                items.append(normalized)
    return items


def _dump_items(items: list[dict[str, Any]]) -> str:
    normalized = []
    for idx, item in enumerate(items):
        current = _normalize_item(item, index=idx)
        if current:
            normalized.append(current)
    return json.dumps(normalized, ensure_ascii=False)


def _compute_total(items: list[dict[str, Any]]) -> int:
    return int(sum(max(1, _safe_int(item.get("proposedPrice") or item.get("unitPrice"), 1)) for item in items))


def _derive_request_side(items: list[dict[str, Any]]) -> str:
    if not items:
        raise ValueError("invalid_items")
    sides = {_norm_side(item.get("side")) for item in items}
    if len(sides) != 1:
        raise ValueError("mixed_directions_not_allowed")
    side = next(iter(sides))
    if side is None:
        raise ValueError("invalid_items")
    return side


def _player_role(player_id: str) -> str:
    if is_user_player(player_id):
        return "NURSERY"
    parsed = _parse_bot_player(player_id)
    if parsed and parsed[0] == "shop":
        return "SHOP"
    return "NURSERY"


def _seller_player_id_from_side(req: TradeRequest | None, items: list[dict[str, Any]], from_player_id: str | None = None, to_player_id: str | None = None) -> str:
    side = _derive_request_side(items)
    source = from_player_id or (req.from_player_id if req else None)
    target = to_player_id or (req.to_player_id if req else None)
    if source is None or target is None:
        raise ValueError("missing_participants")
    return source if side == SELLER_SIDE else target


def _derive_direction(from_player_id: str, to_player_id: str, items: list[dict[str, Any]]) -> str:
    seller_player_id = _seller_player_id_from_side(None, items, from_player_id=from_player_id, to_player_id=to_player_id)
    seller_role = _player_role(seller_player_id)
    return "PLAYER_TO_SHOP" if seller_role != "SHOP" else "SHOP_TO_PLAYER"


def _derive_request_type(items: list[dict[str, Any]], is_counter: bool) -> str:
    if is_counter:
        return "COUNTER_REQUEST"
    side = _derive_request_side(items)
    return "SELL_REQUEST" if side == SELLER_SIDE else "BUY_REQUEST"


def _entity_is_kitten(entity: dict[str, Any] | None) -> bool:
    if not isinstance(entity, dict):
        return False
    age_raw = entity.get("age", entity.get("ageSeasons"))
    age = _safe_int(age_raw, -1)
    if age >= 0:
        return age < ADULT_AGE
    explicit = entity.get("isKitten")
    if isinstance(explicit, bool):
        return explicit
    return False


def _entity_is_sick(entity: dict[str, Any] | None) -> bool:
    if not isinstance(entity, dict):
        return False
    raw_status = str(entity.get("healthStatus") or "").strip().upper()
    if raw_status == "HEALED":
        return False
    if raw_status == "SICK":
        return True
    if isinstance(entity.get("isSick"), bool):
        return bool(entity.get("isSick"))
    disease_type = str(entity.get("diseaseType") or "").strip().upper()
    legacy_disease = str(entity.get("sick") or "").strip().lower()
    return disease_type in {"RINGWORM", "FLEAS", "POISONING", "BROKEN_PAW"} or legacy_disease in {
        "lichen",
        "fleas",
        "poisoning",
        "brokenpaw",
    }


def _only_kittens_trade_meta() -> tuple[str, dict[str, Any]]:
    return "ONLY_KITTENS_CAN_BE_TRADED", {
        "message": "Продавать можно только котят",
    }


def _sick_kittens_trade_meta() -> tuple[str, dict[str, Any]]:
    return "SICK_KITTENS_CANNOT_BE_TRADED", {
        "message": "Больных котят нельзя продавать",
    }


def _ensure_relation(
    db: Session,
    session_id: str,
    player_id: str,
    counterparty_id: str,
    season_number: int,
) -> TradeRelation:
    relation = (
        db.query(TradeRelation)
        .filter(
            TradeRelation.session_id == session_id,
            TradeRelation.player_id == player_id,
            TradeRelation.counterparty_id == counterparty_id,
        )
        .one_or_none()
    )
    if relation:
        return relation
    relation = TradeRelation(
        session_id=session_id,
        player_id=player_id,
        counterparty_id=counterparty_id,
        relation_score=5.0,
        season_number=season_number,
    )
    db.add(relation)
    db.flush()
    return relation


def _ensure_bot_state(db: Session, session_id: str, bot_player_id: str) -> TradeBotState:
    state = (
        db.query(TradeBotState)
        .filter(
            TradeBotState.session_id == session_id,
            TradeBotState.bot_player_id == bot_player_id,
        )
        .one_or_none()
    )
    if state:
        return state
    state = TradeBotState(
        session_id=session_id,
        bot_player_id=bot_player_id,
        coins=240,
        inventory_json=_default_bot_inventory_json(),
    )
    db.add(state)
    db.flush()
    return state


def _participant_meta(player_id: str, viewer_user_id: str | None = None) -> dict[str, Any]:
    if is_user_player(player_id):
        uid = player_id.split(":", 1)[1]
        is_me = bool(viewer_user_id and uid == viewer_user_id)
        return {
            "playerId": player_id,
            "kind": "user",
            "displayName": "Леопольд" if is_me else "Игрок",
            "avatarText": "Я" if is_me else "Игрок",
        }

    parsed = _parse_bot_player(player_id)
    if not parsed:
        return {"playerId": player_id, "kind": "bot", "displayName": player_id, "avatarText": "B"}
    cp_type, cp_id = parsed
    if cp_type == "shop":
        return {
            "playerId": player_id,
            "kind": "shop",
            "displayName": BOT_SHOP_NAMES.get(cp_id, f"Зоомагазин #{cp_id}"),
            "avatarText": "ЗМ",
        }
    return {
        "playerId": player_id,
        "kind": "cattery",
        "displayName": f"Питомник #{cp_id}",
        "avatarText": "ПТ",
    }


def _thread_id(req: TradeRequest) -> str:
    return str(req.thread_id or req.parent_request_id or req.counter_of_request_id or req.id)


def _inherit_expires_at(ttl_seconds: int | None) -> datetime | None:
    ttl = _safe_int(ttl_seconds, 0)
    if ttl <= 0:
        return None
    return datetime.utcnow() + timedelta(seconds=ttl)


def _archive_request_version(req: TradeRequest, *, message_code: str | None = None) -> None:
    req.state = TradeState.AWAITING_CLARIFICATION
    req.next_actor_player_id = None
    req.message_code = message_code or req.message_code or "REQUEST_VERSION_ARCHIVED"
    req.read_by_from = True
    req.read_by_to = True
    req.hidden_by_from = True
    req.hidden_by_to = True
    req.updated_at = datetime.utcnow()


def _create_request_version(
    db: Session,
    base_request: TradeRequest,
    *,
    items: list[dict[str, Any]],
    next_actor_player_id: str,
    state: str,
    message_code: str,
    is_counter: bool = False,
) -> TradeRequest:
    normalized_items = _parse_items(items)
    request_type = (
        "COUNTER_REQUEST"
        if is_counter
        else (base_request.request_type or _derive_request_type(normalized_items, is_counter=False))
    )
    child = TradeRequest(
        session_id=base_request.session_id,
        season_number=base_request.season_number,
        from_player_id=base_request.from_player_id,
        to_player_id=base_request.to_player_id,
        next_actor_player_id=next_actor_player_id,
        thread_id=_thread_id(base_request),
        state=state,
        request_type=request_type,
        direction=base_request.direction or _derive_direction(
            base_request.from_player_id,
            base_request.to_player_id,
            normalized_items,
        ),
        items_json=_dump_items(normalized_items),
        total_price=_compute_total(normalized_items),
        message_code=message_code,
        clarification_reason=None,
        clarification_meta_json=None,
        read_by_from=True,
        read_by_to=True,
        hidden_by_from=False,
        hidden_by_to=False,
        counter_of_request_id=(
            base_request.counter_of_request_id
            or (base_request.id if is_counter else None)
        ),
        parent_request_id=base_request.id,
        clarification_requested_by=None,
        ttl_seconds=base_request.ttl_seconds,
        expires_at=_inherit_expires_at(base_request.ttl_seconds),
    )
    db.add(child)
    db.flush()
    _mark_unread_for_counterparty(child)
    return child


def _parse_clarification_meta(req: TradeRequest) -> dict[str, Any] | None:
    if not req.clarification_meta_json:
        return None
    try:
        raw = json.loads(req.clarification_meta_json)
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _clarification_payload(reason: str | None, *, unavailable_cat_ids: list[str] | None = None, message: str | None = None) -> tuple[str, str]:
    payload: dict[str, Any] = {}
    if unavailable_cat_ids:
        payload["unavailableCatIds"] = unavailable_cat_ids
    if message:
        payload["message"] = message
    return (
        reason or "UNKNOWN",
        json.dumps(payload, ensure_ascii=False) if payload else json.dumps({"message": message or ""}, ensure_ascii=False),
    )


def build_shop_market_view(
    db: Session,
    session_id: str,
    season_number: int,
    viewer_player_id: str,
    bot_player_id: str,
) -> dict[str, dict[str, Any]]:
    market = _market_prices_for_player(session_id, season_number, bot_player_id)
    relation = (
        db.query(TradeRelation)
        .filter(
            TradeRelation.session_id == session_id,
            TradeRelation.player_id == viewer_player_id,
            TradeRelation.counterparty_id == bot_player_id,
        )
        .one_or_none()
    )
    relation_score = float(relation.relation_score) if relation else 5.0
    bot_state = _build_shop_bot_state(
        db=db,
        session_id=session_id,
        season_number=season_number,
        bot_player_id=bot_player_id,
        relation_score=relation_score,
    )
    synced = json.loads(json.dumps(market))
    for color in ["black", "white", "gray", "ginger"]:
        display_buy_price = bot_display_buy_price(bot_state, color)
        if color not in synced:
            continue
        synced[color]["sell"] = display_buy_price
        for sex in ("M", "F"):
            if isinstance(synced[color].get(sex), dict):
                synced[color][sex]["sell"] = display_buy_price
    return synced


def _viewer_status(req: TradeRequest, viewer_player_id: str) -> str:
    if req.state == TradeState.PENDING:
        return "PENDING_INCOMING" if req.next_actor_player_id == viewer_player_id else "PENDING_OUTGOING"
    if req.state == TradeState.COUNTERED:
        return "COUNTERED" if req.next_actor_player_id == viewer_player_id else "PENDING_OUTGOING"
    if req.state == TradeState.NEEDS_CLARIFICATION:
        return "NEEDS_CLARIFICATION" if req.next_actor_player_id == viewer_player_id else "AWAITING_CLARIFICATION"
    if req.state == TradeState.AWAITING_CLARIFICATION:
        return "AWAITING_CLARIFICATION"
    return req.state


def _ui_category_from_status(status: str) -> str:
    if status == "PENDING_INCOMING":
        return "INCOMING"
    if status == "PENDING_OUTGOING":
        return "OUTGOING"
    if status == "COUNTERED":
        return "COUNTER"
    if status == "ACCEPTED":
        return "ACCEPTED_BY_OTHER"
    if status in {"REJECTED", "CANCELLED", "EXPIRED"}:
        return "REJECTED_BY_OTHER"
    if status == "NEEDS_CLARIFICATION":
        return "REQUIRES_CLARIFICATION"
    return "WAITING_FOR_CLARIFICATION"


def _mark_unread_for_counterparty(req: TradeRequest) -> None:
    req.read_by_from = req.next_actor_player_id == req.from_player_id
    req.read_by_to = req.next_actor_player_id == req.to_player_id
    if req.next_actor_player_id == req.from_player_id:
        req.read_by_from = False
        req.read_by_to = True
    elif req.next_actor_player_id == req.to_player_id:
        req.read_by_from = True
        req.read_by_to = False
    else:
        req.read_by_from = False
        req.read_by_to = False


def resolve_request_status(req: TradeRequest, viewer_player_id: str) -> str:
    return _viewer_status(req, viewer_player_id)


def _to_out(req: TradeRequest, viewer_player_id: str, viewer_user_id: str | None = None) -> dict[str, Any]:
    items = _parse_items(req.items_json)
    status = _viewer_status(req, viewer_player_id)
    category = _ui_category_from_status(status)
    read_by_me = req.read_by_from if req.from_player_id == viewer_player_id else req.read_by_to
    hidden_by_me = req.hidden_by_from if req.from_player_id == viewer_player_id else req.hidden_by_to
    unread = not read_by_me and not hidden_by_me
    request_type = req.request_type or _derive_request_type(items, is_counter=bool(req.counter_of_request_id))
    direction = req.direction or _derive_direction(req.from_player_id, req.to_player_id, items)
    parsed_meta = _parse_clarification_meta(req)
    clarification_meta = parsed_meta if req.clarification_reason else None
    decision_meta = parsed_meta if not req.clarification_reason else None

    return {
        "id": req.id,
        "threadId": _thread_id(req),
        "sessionId": req.session_id,
        "seasonId": req.season_number,
        "seasonNumber": req.season_number,
        "createdAt": req.created_at.isoformat() if req.created_at else None,
        "updatedAt": req.updated_at.isoformat() if req.updated_at else None,
        "fromPlayerId": req.from_player_id,
        "toPlayerId": req.to_player_id,
        "type": request_type,
        "direction": direction,
        "status": status,
        "state": status,
        "rawState": req.state,
        "uiCategory": category,
        "icon": UI_CATEGORY_ICON.get(category),
        "isReadBySender": bool(req.read_by_from),
        "isReadByReceiver": bool(req.read_by_to),
        "readByFrom": bool(req.read_by_from),
        "readByTo": bool(req.read_by_to),
        "unread": unread,
        "items": items,
        "totalPrice": int(req.total_price or 0),
        "messageCode": req.message_code,
        "clarificationReason": req.clarification_reason,
        "clarificationMeta": clarification_meta,
        "decisionMeta": decision_meta,
        "counterOfRequestId": req.counter_of_request_id,
        "parentRequestId": req.parent_request_id,
        "ttlSeconds": req.ttl_seconds,
        "fromMeta": _participant_meta(req.from_player_id, viewer_user_id=viewer_user_id),
        "toMeta": _participant_meta(req.to_player_id, viewer_user_id=viewer_user_id),
        "nextActorPlayerId": req.next_actor_player_id,
        "canAct": status in {"PENDING_INCOMING", "COUNTERED", "NEEDS_CLARIFICATION"},
    }


def _expire_stale_requests(db: Session, session_id: str, season_number: int) -> list[TradeRequest]:
    now = datetime.utcnow()
    stale = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.season_number == season_number,
            TradeRequest.state.in_(list(OPEN_STATES)),
            TradeRequest.expires_at.isnot(None),
            TradeRequest.expires_at <= now,
        )
        .all()
    )
    for req in stale:
        if can_transition(req.state, TradeAction.EXPIRE):
            req.state = transition_state(req.state, TradeAction.EXPIRE).to_state
            req.next_actor_player_id = None
            req.message_code = "TTL_EXPIRED"
            req.updated_at = datetime.utcnow()
            req.read_by_from = False
            req.read_by_to = False
    return stale


def list_trade_requests(
    db: Session,
    session_id: str,
    season_number: int,
    viewer_player_id: str,
    viewer_user_id: str,
) -> list[dict[str, Any]]:
    _expire_stale_requests(db, session_id, season_number)
    process_due_bot_responses(db, session_id, season_number)
    db.flush()
    requests = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.season_number == season_number,
            ((TradeRequest.from_player_id == viewer_player_id) | (TradeRequest.to_player_id == viewer_player_id)),
        )
        .order_by(TradeRequest.updated_at.desc(), TradeRequest.created_at.desc())
        .all()
    )
    out: list[dict[str, Any]] = []
    for req in requests:
        hidden_for_viewer = req.hidden_by_from if req.from_player_id == viewer_player_id else req.hidden_by_to
        if hidden_for_viewer:
            continue
        out.append(_to_out(req, viewer_player_id=viewer_player_id, viewer_user_id=viewer_user_id))
    return out


def _inventory_by_type(inventory_json: str) -> dict[str, int]:
    parsed = crud._parse_inventory(inventory_json or "{}")
    return {
        color: _safe_int(parsed["counts"].get(color, {}).get("M"), 0) + _safe_int(parsed["counts"].get(color, {}).get("F"), 0)
        for color in ["black", "white", "gray", "ginger"]
    }


def _recent_accepted_prices_by_type(db: Session, session_id: str, bot_player_id: str) -> dict[str, list[int]]:
    requests = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.state == TradeState.ACCEPTED,
            ((TradeRequest.from_player_id == bot_player_id) | (TradeRequest.to_player_id == bot_player_id)),
        )
        .order_by(TradeRequest.updated_at.desc())
        .limit(20)
        .all()
    )
    values: dict[str, list[int]] = {}
    for req in requests:
        for item in _parse_items(req.items_json):
            color = _norm_color(item.get("catType"))
            if not color:
                continue
            values.setdefault(color, []).append(max(1, _safe_int(item.get("proposedPrice"), 1)))
    return {key: prices[:5] for key, prices in values.items()}


def _pending_requests_count(db: Session, session_id: str, bot_player_id: str) -> int:
    return (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.state.in_(list(OPEN_STATES)),
            TradeRequest.next_actor_player_id == bot_player_id,
        )
        .count()
    )


def _build_shop_bot_state(
    db: Session,
    session_id: str,
    season_number: int,
    bot_player_id: str,
    relation_score: float,
) -> ShopBotState:
    bot_state_row = _ensure_bot_state(db, session_id, bot_player_id)
    market = _market_prices_for_player(session_id, season_number, bot_player_id)
    inventory_by_type = _inventory_by_type(bot_state_row.inventory_json or "{}")
    sell_values = [max(1, _safe_int(market.get(color, {}).get("sell"), 1)) for color in market]
    avg_sell = sum(sell_values) / max(1, len(sell_values))

    demand_by_type: dict[str, int] = {}
    expected_resale_value: dict[str, int] = {}
    for color in ["black", "white", "gray", "ginger"]:
        market_value = max(1, _safe_int(market.get(color, {}).get("sell"), 1))
        expected_resale_value[color] = market_value
        demand = 0
        if market_value >= avg_sell + 2:
            demand += 2
        elif market_value >= avg_sell + 1:
            demand += 1
        elif market_value <= avg_sell - 2:
            demand -= 2
        elif market_value <= avg_sell - 1:
            demand -= 1

        stock = inventory_by_type.get(color, 0)
        if stock == 0:
            demand += 1
        elif stock >= 5:
            demand -= 1
        demand_by_type[color] = max(-2, min(2, demand))

    return ShopBotState(
        botId=bot_player_id,
        cash=max(0, _safe_int(bot_state_row.coins, 0)),
        relationScoreToPlayer=relation_score,
        inventoryByType=inventory_by_type,
        currentDemandByType=demand_by_type,
        expectedResaleValueByType=expected_resale_value,
        recentAcceptedPricesByType=_recent_accepted_prices_by_type(db, session_id, bot_player_id),
        pendingRequestsCount=_pending_requests_count(db, session_id, bot_player_id),
        archetype=shop_bot_archetype(bot_player_id),
    )


def _market_prices_for_player(session_id: str, season_number: int, player_id: str) -> dict[str, dict[str, Any]]:
    parsed = _parse_bot_player(player_id)
    if not parsed:
        return crud.generate_market_prices(session_id, season_number, None, None)
    cp_type, cp_id = parsed
    return crud.generate_market_prices(session_id, season_number, cp_type, cp_id)


def _make_inventory_moved(sex: str | None) -> dict[str, int]:
    return {"M": 1 if sex == "M" else 0, "F": 1 if sex == "F" else 0}


def _take_inventory(counts: dict[str, dict[str, int]], color: str, sex: str | None, qty: int) -> tuple[bool, dict[str, int]]:
    removed = {"M": 0, "F": 0}
    if qty <= 0:
        return False, removed
    if sex in {"M", "F"}:
        available = _safe_int(counts.get(color, {}).get(sex), 0)
        if available < qty:
            return False, removed
        counts[color][sex] = available - qty
        removed[sex] = qty
        return True, removed

    available_m = _safe_int(counts.get(color, {}).get("M"), 0)
    available_f = _safe_int(counts.get(color, {}).get("F"), 0)
    if available_m + available_f < qty:
        return False, removed
    take_m = min(available_m, qty)
    take_f = qty - take_m
    counts[color]["M"] = available_m - take_m
    counts[color]["F"] = available_f - take_f
    removed["M"] = take_m
    removed["F"] = take_f
    return True, removed


def _add_inventory(counts: dict[str, dict[str, int]], color: str, moved: dict[str, int]) -> None:
    for sex in ("M", "F"):
        qty = max(0, _safe_int(moved.get(sex), 0))
        counts[color][sex] = _safe_int(counts.get(color, {}).get(sex), 0) + qty


def _remove_entities(
    entities: list[dict[str, Any]],
    color: str,
    moved: dict[str, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    left = {"M": max(0, _safe_int(moved.get("M"), 0)), "F": max(0, _safe_int(moved.get("F"), 0))}
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for entity in entities:
        e_color = _norm_color(entity.get("color"))
        e_sex = _norm_sex(entity.get("sex"))
        if e_color == color and e_sex in {"M", "F"} and left[e_sex] > 0:
            left[e_sex] -= 1
            removed.append(entity)
            continue
        kept.append(entity)
    return kept, removed


def _append_entities(
    entities: list[dict[str, Any]],
    color: str,
    moved: dict[str, int],
) -> list[dict[str, Any]]:
    next_entities = list(entities)
    for sex in ("M", "F"):
        qty = max(0, _safe_int(moved.get(sex), 0))
        for _ in range(qty):
            next_entities.append(
                {
                    "id": f"inv-{uuid.uuid4().hex[:12]}",
                    "color": color,
                    "sex": sex,
                    "age": 0,
                    "isKitten": True,
                    "hungry": False,
                    "fedThisSeason": True,
                    "isSick": False,
                    "diseaseType": None,
                    "healthStatus": "HEALTHY",
                    "healedAtSeason": None,
                }
            )
    return next_entities


def _take_exact_item(
    inventory: dict[str, Any],
    *,
    cat_id: str | None,
    color: str,
    sex: str | None,
) -> tuple[bool, dict[str, int], list[dict[str, Any]], str | None, dict[str, Any] | None]:
    entities = list(inventory.get("entities", []))
    counts = inventory["counts"]

    if cat_id and entities:
        for index, entity in enumerate(entities):
            if str(entity.get("id")) != cat_id:
                continue
            entity_color = _norm_color(entity.get("color"))
            entity_sex = _norm_sex(entity.get("sex"))
            if entity_color != color or (sex and entity_sex != sex):
                reason, meta_json = _clarification_payload(
                    "CAT_STATE_CHANGED",
                    unavailable_cat_ids=[cat_id],
                    message="Котик изменил состояние и больше не подходит для сделки",
                )
                return False, {"M": 0, "F": 0}, [], reason, json.loads(meta_json)
            if not _entity_is_kitten(entity):
                reason, meta_json = _only_kittens_trade_meta()
                return False, {"M": 0, "F": 0}, [], reason, meta_json
            if _entity_is_sick(entity):
                reason, meta_json = _sick_kittens_trade_meta()
                return False, {"M": 0, "F": 0}, [], reason, meta_json
            entities.pop(index)
            inventory["entities"] = entities
            moved = _make_inventory_moved(entity_sex)
            counts[color][entity_sex] = max(0, _safe_int(counts.get(color, {}).get(entity_sex), 0) - 1)
            return True, moved, [entity], None, None

        reason, meta_json = _clarification_payload(
            "CAT_NOT_AVAILABLE",
            unavailable_cat_ids=[cat_id],
            message="Котик уже недоступен для сделки",
        )
        return False, {"M": 0, "F": 0}, [], reason, json.loads(meta_json)

    if entities:
        matched_indexes: list[int] = []
        kitten_index: int | None = None
        sick_kitten_found = False
        for index, entity in enumerate(entities):
            entity_color = _norm_color(entity.get("color"))
            entity_sex = _norm_sex(entity.get("sex"))
            if entity_color != color or (sex and entity_sex != sex):
                continue
            matched_indexes.append(index)
            if not _entity_is_kitten(entity):
                continue
            if _entity_is_sick(entity):
                sick_kitten_found = True
                continue
            if kitten_index is None:
                kitten_index = index
        if matched_indexes and kitten_index is None:
            if sick_kitten_found:
                reason, meta_json = _sick_kittens_trade_meta()
                return False, {"M": 0, "F": 0}, [], reason, meta_json
            reason, meta_json = _only_kittens_trade_meta()
            return False, {"M": 0, "F": 0}, [], reason, meta_json
        if kitten_index is not None:
            entity = entities.pop(kitten_index)
            entity_sex = _norm_sex(entity.get("sex")) or "M"
            inventory["entities"] = entities
            moved = _make_inventory_moved(entity_sex)
            counts[color][entity_sex] = max(0, _safe_int(counts.get(color, {}).get(entity_sex), 0) - 1)
            return True, moved, [entity], None, None

    ok, moved = _take_inventory(counts, color, sex, 1)
    if not ok:
        reason, meta_json = _clarification_payload(
            "CAT_ALREADY_SOLD",
            unavailable_cat_ids=[cat_id] if cat_id else None,
            message="Котик уже продан или недоступен",
        )
        return False, {"M": 0, "F": 0}, [], reason, json.loads(meta_json)

    seller_entities, moved_entities = _remove_entities(
        entities,
        color=color,
        moved=moved,
    )
    inventory["entities"] = seller_entities
    return True, moved, moved_entities, None, None


def _validate_user_sell_items(session: GameSession, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    inventory = crud._parse_inventory(session.inventory_json or "{}")
    for item in items:
        color = _norm_color(item.get("catType"))
        sex = _norm_sex(item.get("catSex"))
        cat_id = str(item.get("catId") or "")
        if color is None:
            raise ValueError("invalid_items")
        ok, _, _, reason, _ = _take_exact_item(
            inventory,
            cat_id=cat_id,
            color=color,
            sex=sex,
        )
        if not ok:
            raise ValueError(reason or "invalid_items")


def _apply_acceptance_transaction(
    db: Session,
    session: GameSession,
    req: TradeRequest,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    items = _parse_items(req.items_json)
    if not items:
        return False, "EMPTY_ITEMS", None

    season_number = int(req.season_number)
    player_ledger: dict[str, Any] = {}
    bot_ledgers: dict[str, dict[str, Any]] = {}

    def get_ledger(player_id: str) -> dict[str, Any]:
        if is_user_player(player_id):
            if player_ledger:
                return player_ledger
            est = crud.estimate_state(db, session.id, season_number)
            inv = crud._parse_inventory(session.inventory_json or "{}")
            player_ledger.update(
                {
                    "playerId": player_id,
                    "kind": "user",
                    "coins": max(0, _safe_int(est.get("coins"), 0)),
                    "inventory": {
                        "counts": json.loads(json.dumps(inv.get("counts", {}))),
                        "entities": list(inv.get("entities", [])),
                    },
                    "events": [],
                }
            )
            return player_ledger

        if player_id in bot_ledgers:
            return bot_ledgers[player_id]
        bot_state = _ensure_bot_state(db, session.id, player_id)
        inv = crud._parse_inventory(bot_state.inventory_json or "{}")
        ledger = {
            "playerId": player_id,
            "kind": "bot",
            "state": bot_state,
            "coins": max(0, _safe_int(bot_state.coins, 0)),
            "inventory": {
                "counts": json.loads(json.dumps(inv.get("counts", {}))),
                "entities": list(inv.get("entities", [])),
            },
        }
        bot_ledgers[player_id] = ledger
        return ledger

    side = _derive_request_side(items)
    for item in items:
        color = _norm_color(item.get("catType"))
        sex = _norm_sex(item.get("catSex"))
        cat_id = str(item.get("catId") or "")
        proposed_price = max(1, _safe_int(item.get("proposedPrice") or item.get("unitPrice"), 1))
        if color is None:
            return False, "INVALID_ITEM", None

        if side == BUYER_SIDE:
            buyer_id = req.from_player_id
            seller_id = req.to_player_id
        else:
            buyer_id = req.to_player_id
            seller_id = req.from_player_id

        buyer = get_ledger(buyer_id)
        seller = get_ledger(seller_id)
        if buyer["coins"] < proposed_price:
            return False, "INSUFFICIENT_FUNDS", {"message": "Недостаточно денег для завершения сделки"}

        ok, moved, moved_entities, clarification_reason, clarification_meta = _take_exact_item(
            seller["inventory"],
            cat_id=cat_id,
            color=color,
            sex=sex,
        )
        if not ok:
            return False, clarification_reason, clarification_meta

        buyer["coins"] -= proposed_price
        seller["coins"] += proposed_price
        _add_inventory(buyer["inventory"]["counts"], color, moved)
        if moved_entities:
            buyer["inventory"]["entities"] = list(buyer["inventory"]["entities"]) + moved_entities
        else:
            buyer["inventory"]["entities"] = _append_entities(
                buyer["inventory"]["entities"],
                color=color,
                moved=moved,
            )

        if buyer["kind"] == "user":
            buyer["events"].append(
                {
                    "action": "buy",
                    "catType": color,
                    "catSex": sex,
                    "qty": 1,
                    "unitPrice": proposed_price,
                    "counterpartyType": (_parse_bot_player(seller_id) or ("shop", 0))[0],
                    "counterpartyId": (_parse_bot_player(seller_id) or ("shop", 0))[1],
                    "entityId": cat_id or None,
                }
            )
        if seller["kind"] == "user":
            seller["events"].append(
                {
                    "action": "sell",
                    "catType": color,
                    "catSex": sex,
                    "qty": 1,
                    "unitPrice": proposed_price,
                    "counterpartyType": (_parse_bot_player(buyer_id) or ("shop", 0))[0],
                    "counterpartyId": (_parse_bot_player(buyer_id) or ("shop", 0))[1],
                    "entityId": cat_id or None,
                }
            )

    if player_ledger:
        session.inventory_json = crud._serialize_inventory(player_ledger["inventory"])
        for payload in player_ledger["events"]:
            db.add(
                GameEvent(
                    session_id=session.id,
                    season_number=season_number,
                    event_type="trade_market",
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            )

    for ledger in bot_ledgers.values():
        state = ledger["state"]
        state.coins = max(0, _safe_int(ledger["coins"], 0))
        state.inventory_json = crud._serialize_inventory(ledger["inventory"])
        state.updated_at = datetime.utcnow()

    return True, None, None


def _recalc_relation_on_created_request(
    db: Session,
    relation: TradeRelation,
    session_id: str,
    season_number: int,
    counterparty_id: str,
    items: list[dict[str, Any]],
) -> None:
    relation.sent_requests_in_season = max(0, _safe_int(relation.sent_requests_in_season, 0)) + 1
    spam_overflow = max(0, relation.sent_requests_in_season - 5)
    if spam_overflow > 0:
        relation.relation_score = update_relation(
            relation.relation_score,
            {"type": "spam", "extra": 1},
        )

    bot_state = _build_shop_bot_state(
        db=db,
        session_id=session_id,
        season_number=season_number,
        bot_player_id=counterparty_id,
        relation_score=relation.relation_score,
    )
    worst_overprice_ratio = 0.0
    has_good_price = False
    for item in items:
        if str(item.get("side")).upper() != SELLER_SIDE:
            continue
        color = _norm_color(item.get("catType"))
        offer = max(1, _safe_int(item.get("proposedPrice"), 1))
        if color is None:
            continue
        display_buy_price = bot_display_buy_price(bot_state, color)
        if display_buy_price <= 0:
            continue
        if offer <= display_buy_price:
            has_good_price = True
        else:
            worst_overprice_ratio = max(
                worst_overprice_ratio,
                max(0.0, (offer / display_buy_price) - 1.0),
            )

    if has_good_price:
        relation.relation_score = update_relation(relation.relation_score, {"type": "price_ok"})
    elif worst_overprice_ratio > 0:
        relation.relation_score = update_relation(
            relation.relation_score,
            {"type": "overpriced", "ratio": worst_overprice_ratio},
        )


def _set_request_clarification(
    req: TradeRequest,
    *,
    seller_player_id: str,
    clarification_reason: str | None,
    clarification_meta: dict[str, Any] | None,
    message_code: str | None = None,
) -> None:
    req.state = TradeState.NEEDS_CLARIFICATION
    req.next_actor_player_id = seller_player_id
    req.clarification_requested_by = _other_party(req, seller_player_id)
    req.clarification_reason = clarification_reason or "UNKNOWN"
    req.clarification_meta_json = json.dumps(clarification_meta or {}, ensure_ascii=False)
    req.message_code = message_code or "REQUIRES_CLARIFICATION"
    req.read_by_from = False
    req.read_by_to = False


def request_expects_bot_response(req: TradeRequest) -> bool:
    return bool(req.next_actor_player_id and _parse_bot_player(req.next_actor_player_id) and req.state in OPEN_STATES)


def process_due_bot_responses(
    db: Session,
    session_id: str,
    season_number: int,
) -> list[tuple[TradeRequest, str]]:
    session = db.get(GameSession, session_id)
    if not session:
        return []

    now = datetime.utcnow()
    processed: list[tuple[TradeRequest, str]] = []
    pending_requests = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.season_number == season_number,
            TradeRequest.state.in_(list(OPEN_STATES)),
        )
        .order_by(TradeRequest.updated_at.asc(), TradeRequest.created_at.asc())
        .all()
    )

    for req in pending_requests:
        if not request_expects_bot_response(req):
            continue
        base_time = req.updated_at or req.created_at
        if not base_time:
            continue
        delay_seconds = bot_response_delay_seconds_for_request(req.id)
        if (now - base_time).total_seconds() < delay_seconds:
            continue
        previous_state = req.state
        updated = process_bot_response(db, session, req)
        if not updated:
            continue
        processed.append((req, previous_state))

    return processed


def process_bot_response(
    db: Session,
    session: GameSession,
    req: TradeRequest,
) -> TradeRequest | None:
    if not request_expects_bot_response(req):
        return None

    bot_player_id = req.next_actor_player_id
    user_party = req.from_player_id if is_user_player(req.from_player_id) else req.to_player_id
    relation = _ensure_relation(
        db=db,
        session_id=session.id,
        player_id=user_party,
        counterparty_id=bot_player_id,
        season_number=req.season_number,
    )
    bot_state = _build_shop_bot_state(
        db=db,
        session_id=session.id,
        season_number=req.season_number,
        bot_player_id=bot_player_id,
        relation_score=relation.relation_score,
    )
    decision: OfferDecision = decide_on_offer(
        request_items=_parse_items(req.items_json),
        bot_state=bot_state,
        request_id=req.id,
        rng=random.Random(f"bot-response:{req.id}:{req.updated_at.isoformat() if req.updated_at else '0'}"),
    )
    if req.state in {TradeState.NEEDS_CLARIFICATION, TradeState.AWAITING_CLARIFICATION} and decision.action == "COUNTER":
        counter_items = _parse_items(decision.counter_items or _parse_items(req.items_json))
        _archive_request_version(req, message_code="CLARIFICATION_HANDLED")
        child = _create_request_version(
            db,
            req,
            items=counter_items,
            next_actor_player_id=_other_party(req, bot_player_id),
            state=TradeState.COUNTERED,
            message_code=decision.message_code or "BOT_COUNTERED",
            is_counter=True,
        )
        child.clarification_meta_json = json.dumps(decision.decision_meta or {}, ensure_ascii=False)
        return child

    if decision.action == "ACCEPT" and can_transition(req.state, TradeAction.ACCEPT):
        ok, reason, clarification_meta = _apply_acceptance_transaction(db, session, req)
        if ok:
            req.state = transition_state(req.state, TradeAction.ACCEPT).to_state
            req.next_actor_player_id = None
            req.message_code = decision.message_code or "BOT_ACCEPTED"
            req.read_by_from = False
            req.read_by_to = True
            req.clarification_reason = None
            req.clarification_meta_json = None
            return req

        seller_player_id = _seller_player_id_from_side(req, _parse_items(req.items_json))
        _set_request_clarification(
            req,
            seller_player_id=seller_player_id,
            clarification_reason=reason,
            clarification_meta=clarification_meta,
            message_code=reason or "REQUIRES_CLARIFICATION",
        )
        return req

    if decision.action == "COUNTER" and can_transition(req.state, TradeAction.COUNTER):
        counter_items = _parse_items(decision.counter_items or _parse_items(req.items_json))
        req.state = transition_state(req.state, TradeAction.COUNTER).to_state
        req.next_actor_player_id = _other_party(req, bot_player_id)
        req.request_type = "COUNTER_REQUEST"
        req.items_json = _dump_items(counter_items)
        req.total_price = _compute_total(counter_items)
        req.message_code = decision.message_code or "BOT_COUNTERED"
        req.counter_of_request_id = req.counter_of_request_id or req.id
        req.clarification_reason = None
        req.clarification_meta_json = json.dumps(decision.decision_meta or {}, ensure_ascii=False)
        _mark_unread_for_counterparty(req)
        return req

    if can_transition(req.state, TradeAction.REJECT):
        req.state = transition_state(req.state, TradeAction.REJECT).to_state
        req.next_actor_player_id = None
        req.message_code = decision.message_code or "BOT_REJECTED"
        req.clarification_reason = None
        req.clarification_meta_json = json.dumps(decision.decision_meta or {}, ensure_ascii=False)
        req.read_by_from = False
        req.read_by_to = True
        return req
    return req


def create_trade_request(
    db: Session,
    session: GameSession,
    season_number: int,
    from_player_id: str,
    to_player_id: str,
    items: list[dict[str, Any]],
    ttl_seconds: int | None = None,
) -> TradeRequest:
    normalized_items = _parse_items(items)
    if not normalized_items:
        raise ValueError("invalid_items")
    if from_player_id == to_player_id:
        raise ValueError("same_player")
    side = _derive_request_side(normalized_items)
    seller_player_id = _seller_player_id_from_side(
        None,
        normalized_items,
        from_player_id=from_player_id,
        to_player_id=to_player_id,
    )
    if is_user_player(from_player_id) and seller_player_id == from_player_id:
        _validate_user_sell_items(session, normalized_items)

    expires_at = None
    ttl = None
    if ttl_seconds is not None and _safe_int(ttl_seconds) > 0:
        ttl = _safe_int(ttl_seconds)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    req = TradeRequest(
        session_id=session.id,
        season_number=season_number,
        from_player_id=from_player_id,
        to_player_id=to_player_id,
        next_actor_player_id=to_player_id,
        state=TradeState.PENDING,
        request_type="SELL_REQUEST" if side == SELLER_SIDE else "BUY_REQUEST",
        direction=_derive_direction(from_player_id, to_player_id, normalized_items),
        items_json=_dump_items(normalized_items),
        total_price=_compute_total(normalized_items),
        message_code="PENDING_REVIEW",
        clarification_reason=None,
        clarification_meta_json=None,
        read_by_from=True,
        read_by_to=False,
        hidden_by_from=False,
        hidden_by_to=False,
        parent_request_id=None,
        counter_of_request_id=None,
        ttl_seconds=ttl,
        expires_at=expires_at,
    )
    db.add(req)
    db.flush()
    if not req.thread_id:
        req.thread_id = req.id

    if not is_user_player(to_player_id):
        relation = _ensure_relation(
            db=db,
            session_id=session.id,
            player_id=from_player_id,
            counterparty_id=to_player_id,
            season_number=season_number,
        )
        _recalc_relation_on_created_request(
            db=db,
            relation=relation,
            session_id=session.id,
            season_number=season_number,
            counterparty_id=to_player_id,
            items=normalized_items,
        )

    db.flush()
    return req


def maybe_create_bot_incoming_request(
    db: Session,
    session: GameSession,
    season_number: int,
    user_player_id_value: str,
) -> TradeRequest | None:
    seed_event = (
        db.query(GameEvent)
        .filter(
            GameEvent.session_id == session.id,
            GameEvent.season_number == season_number,
            GameEvent.event_type == "trade_bot_incoming_seeded",
        )
        .first()
    )
    if seed_event:
        return None

    rnd = random.Random(f"bot-seed:{session.id}:{season_number}")
    if rnd.random() > 0.45:
        db.add(
            GameEvent(
                session_id=session.id,
                season_number=season_number,
                event_type="trade_bot_incoming_seeded",
                payload_json=json.dumps({"created": False}, ensure_ascii=False),
            )
        )
        db.flush()
        return None

    if session.assigned_role == "cattery":
        bot_type = "shop"
        bot_id = rnd.choice([1, 2, 3, 4, 5])
    else:
        bot_type = "cattery"
        bot_id = rnd.choice([2, 3, 4, 5, 6])

    bot_player_id = counterparty_player_id(bot_type, bot_id)
    relation = _ensure_relation(
        db=db,
        session_id=session.id,
        player_id=user_player_id_value,
        counterparty_id=bot_player_id,
        season_number=season_number,
    )
    if relation.relation_score <= 0:
        db.add(
            GameEvent(
                session_id=session.id,
                season_number=season_number,
                event_type="trade_bot_incoming_seeded",
                payload_json=json.dumps({"created": False, "reason": "relation_zero"}, ensure_ascii=False),
            )
        )
        db.flush()
        return None

    weighted_types = [("ginger", 0.35), ("gray", 0.30), ("black", 0.20), ("white", 0.15)]
    ticket = rnd.random()
    cursor = 0.0
    cat_type = "gray"
    for color, weight in weighted_types:
        cursor += weight
        if ticket <= cursor:
            cat_type = color
            break

    market_prices = _market_prices_for_player(session.id, season_number, bot_player_id)
    market_sell = max(1, _safe_int(market_prices.get(cat_type, {}).get("sell"), 10))
    fair_price = max(1, int(round(market_sell * rnd.uniform(0.75, 0.95))))
    cat_sex = rnd.choice(["M", "F"])

    req = create_trade_request(
        db=db,
        session=session,
        season_number=season_number,
        from_player_id=bot_player_id,
        to_player_id=user_player_id_value,
        items=[
            {
                "catType": cat_type,
                "catColor": cat_type,
                "catSex": cat_sex,
                "catId": f"bot-{bot_player_id}-{cat_type}-{cat_sex}-{uuid.uuid4().hex[:8]}",
                "proposedPrice": fair_price,
                "side": "BUY",
                "currency": "COIN",
            }
        ],
        ttl_seconds=180,
    )
    db.add(
        GameEvent(
            session_id=session.id,
            season_number=season_number,
            event_type="trade_bot_incoming_seeded",
            payload_json=json.dumps({"created": True, "requestId": req.id, "botPlayerId": bot_player_id}, ensure_ascii=False),
        )
    )
    db.flush()
    return req


def get_trade_request(db: Session, session_id: str, request_id: str) -> TradeRequest | None:
    return (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session_id,
            TradeRequest.id == request_id,
        )
        .one_or_none()
    )


def apply_trade_action(
    db: Session,
    session: GameSession,
    request_obj: TradeRequest,
    actor_player_id: str,
    action: str,
    counter_items: list[dict[str, Any]] | None = None,
    message_code: str | None = None,
) -> TradeRequest:
    if actor_player_id not in {request_obj.from_player_id, request_obj.to_player_id}:
        raise ValueError("forbidden_actor")

    if action == "ack":
        if request_obj.from_player_id == actor_player_id:
            request_obj.read_by_from = True
            if is_terminal(request_obj.state):
                request_obj.hidden_by_from = True
        if request_obj.to_player_id == actor_player_id:
            request_obj.read_by_to = True
            if is_terminal(request_obj.state):
                request_obj.hidden_by_to = True
        request_obj.updated_at = datetime.utcnow()
        return request_obj

    if request_obj.next_actor_player_id and request_obj.next_actor_player_id != actor_player_id:
        raise ValueError("not_your_turn")

    current_items = _parse_items(request_obj.items_json)
    seller_player_id = _seller_player_id_from_side(request_obj, current_items)

    if action == "cancel":
        if request_obj.from_player_id != actor_player_id:
            raise ValueError("only_initiator_can_cancel")
        if not can_transition(request_obj.state, TradeAction.CANCEL):
            raise ValueError("invalid_transition")
        request_obj.state = transition_state(request_obj.state, TradeAction.CANCEL).to_state
        request_obj.next_actor_player_id = None
        request_obj.message_code = message_code or "CANCELLED_BY_INITIATOR"
        request_obj.clarification_reason = None
        request_obj.clarification_meta_json = None
        request_obj.read_by_from = True
        request_obj.read_by_to = False
        parsed = _parse_bot_player(request_obj.to_player_id)
        if parsed:
            relation = _ensure_relation(
                db=db,
                session_id=session.id,
                player_id=request_obj.from_player_id,
                counterparty_id=request_obj.to_player_id,
                season_number=request_obj.season_number,
            )
            relation.cancel_count_in_season = max(0, _safe_int(relation.cancel_count_in_season, 0)) + 1
            relation.relation_score = update_relation(relation.relation_score, {"type": "cancel"})
        return request_obj

    if action == "accept":
        if not can_transition(request_obj.state, TradeAction.ACCEPT):
            raise ValueError("invalid_transition")
        ok, reason, clarification_meta = _apply_acceptance_transaction(db, session, request_obj)
        if ok:
            prior_state = request_obj.state
            request_obj.state = transition_state(request_obj.state, TradeAction.ACCEPT).to_state
            request_obj.next_actor_player_id = None
            request_obj.message_code = message_code or "TRADE_ACCEPTED"
            request_obj.clarification_reason = None
            request_obj.clarification_meta_json = None
            request_obj.read_by_from = False
            request_obj.read_by_to = False
            if prior_state == TradeState.COUNTERED:
                counterparty = _other_party(request_obj, actor_player_id)
                parsed = _parse_bot_player(counterparty)
                if parsed:
                    relation = _ensure_relation(
                        db=db,
                        session_id=session.id,
                        player_id=actor_player_id if is_user_player(actor_player_id) else request_obj.from_player_id,
                        counterparty_id=counterparty,
                        season_number=request_obj.season_number,
                    )
                    relation.relation_score = update_relation(relation.relation_score, {"type": "counter_accepted"})
            return request_obj

        if can_transition(request_obj.state, TradeAction.REQUEST_CLARIFICATION):
            request_obj.state = transition_state(request_obj.state, TradeAction.REQUEST_CLARIFICATION).to_state
            request_obj.next_actor_player_id = seller_player_id
            request_obj.clarification_requested_by = actor_player_id
            request_obj.clarification_reason = reason or "UNKNOWN"
            request_obj.clarification_meta_json = json.dumps(clarification_meta or {}, ensure_ascii=False)
            request_obj.message_code = message_code or reason or "REQUIRES_CLARIFICATION"
            request_obj.read_by_from = False
            request_obj.read_by_to = False
            return request_obj
        raise ValueError("cannot_apply_insufficient_transition")

    if action == "reject":
        if not can_transition(request_obj.state, TradeAction.REJECT):
            raise ValueError("invalid_transition")
        request_obj.state = transition_state(request_obj.state, TradeAction.REJECT).to_state
        request_obj.next_actor_player_id = None
        request_obj.message_code = message_code or "TRADE_REJECTED"
        request_obj.clarification_reason = None
        request_obj.clarification_meta_json = None
        request_obj.read_by_from = False
        request_obj.read_by_to = False
        return request_obj

    if action == "counter":
        if not can_transition(request_obj.state, TradeAction.COUNTER):
            raise ValueError("invalid_transition")
        normalized_counter = _parse_items(counter_items or [])
        if not normalized_counter:
            raise ValueError("invalid_counter_items")
        if _derive_request_side(normalized_counter) != _derive_request_side(current_items):
            raise ValueError("mixed_directions_not_allowed")
        counter_seller_player_id = _seller_player_id_from_side(request_obj, normalized_counter)
        if is_user_player(actor_player_id) and counter_seller_player_id == actor_player_id:
            _validate_user_sell_items(session, normalized_counter)
        request_obj.state = transition_state(request_obj.state, TradeAction.COUNTER).to_state
        request_obj.next_actor_player_id = _other_party(request_obj, actor_player_id)
        request_obj.request_type = "COUNTER_REQUEST"
        request_obj.items_json = _dump_items(normalized_counter)
        request_obj.total_price = _compute_total(normalized_counter)
        request_obj.message_code = message_code or "COUNTER_OFFER"
        request_obj.counter_of_request_id = request_obj.counter_of_request_id or request_obj.id
        request_obj.parent_request_id = request_obj.parent_request_id or request_obj.id
        request_obj.clarification_reason = None
        request_obj.clarification_meta_json = None
        _mark_unread_for_counterparty(request_obj)
        return request_obj

    if action == "request_clarification":
        if not can_transition(request_obj.state, TradeAction.REQUEST_CLARIFICATION):
            raise ValueError("invalid_transition")
        request_obj.state = transition_state(request_obj.state, TradeAction.REQUEST_CLARIFICATION).to_state
        request_obj.next_actor_player_id = seller_player_id
        request_obj.clarification_requested_by = actor_player_id
        request_obj.clarification_reason = "UNKNOWN"
        request_obj.clarification_meta_json = json.dumps({"message": "Нужно обновить состав или цену заявки"}, ensure_ascii=False)
        request_obj.message_code = message_code or "REQUIRES_CLARIFICATION"
        _mark_unread_for_counterparty(request_obj)
        return request_obj

    if action == "clarify":
        if not can_transition(request_obj.state, TradeAction.CLARIFY):
            raise ValueError("invalid_transition")
        normalized_counter = _parse_items(counter_items or current_items)
        if not normalized_counter:
            raise ValueError("invalid_counter_items")
        if _derive_request_side(normalized_counter) != _derive_request_side(current_items):
            raise ValueError("mixed_directions_not_allowed")
        counter_seller_player_id = _seller_player_id_from_side(request_obj, normalized_counter)
        if is_user_player(actor_player_id) and counter_seller_player_id == actor_player_id:
            _validate_user_sell_items(session, normalized_counter)
        _archive_request_version(request_obj, message_code="CLARIFICATION_HANDLED")
        return _create_request_version(
            db,
            request_obj,
            items=normalized_counter,
            next_actor_player_id=_other_party(request_obj, actor_player_id),
            state=TradeState.PENDING,
            message_code=message_code or "CLARIFIED_RESUBMITTED",
            is_counter=False,
        )

    raise ValueError("unsupported_action")
