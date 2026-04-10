import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .models import User, CandidateProfile
import math
from sqlalchemy import and_
from .models import GameEvent


def create_demo_user(db: Session, role: str, full_name: str) -> User:
    user = User(role=role)
    db.add(user)
    db.flush()  # получить user.id

    # создаём профиль сразу, чтобы фронту было проще
    profile = CandidateProfile(
        user_id=user.id,
        full_name=full_name if role == "candidate" else "",
        skills_json="[]",
        updated_at=datetime.utcnow(),
    )
    db.add(profile)

    db.commit()
    db.refresh(user)
    return user


def get_profile(db: Session, user_id: str) -> CandidateProfile | None:
    return db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).one_or_none()


def update_profile(db: Session, user_id: str, data: dict) -> CandidateProfile:
    profile = get_profile(db, user_id)
    if not profile:
        profile = CandidateProfile(user_id=user_id)
        db.add(profile)

    profile.full_name = data["fullName"]
    profile.city = data["city"]
    profile.university = data["university"]
    profile.program = data["program"]
    profile.study_year = data["studyYear"]
    profile.skills_json = json.dumps(data.get("skills", []), ensure_ascii=False)
    profile.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    return profile

import random
from .models import GameSession, Season, GameEvent, CompetencyResult, GameProgress, CatteryCompetitor
from .game_config import (
    ADULT_AGE,
    CONFIG_ROLE_PLAYER,
    CONFIG_START_COINS,
    CONFIG_START_HOUSES,
    CONFIG_START_KITTENS,
    CONFIG_START_PRODUCTION_MODE,
)
from .cattery_ai import ensure_competitors_for_session, advance_competitors_for_season

START_COINS = CONFIG_START_COINS
SEASONS_TOTAL = 13

UTILITY_COST = {"cattery": 3, "petshop": 1}
CREDIT_MAX = 35
CREDIT_RATES = {"consumer": 0.05, "investment": 0.10, "special": 0.15}

SEASON_SECONDS = {
    1: 600,
    2: 300,
    3: 300,
    4: 300,
    5: 900,
    6: 300,
    7: 300,
    8: 300,
    9: 300,
    10: 900,
    11: 300,
    12: 300,
    13: 600,
}

CAT_TYPES = ["black", "white", "ginger", "gray"]
CAT_SEXES = ["M", "F"]
COUNTERPARTY_TYPES = {"shop", "cattery"}


def _build_start_inventory_for_player(role: str, seed: str) -> dict:
    counts = _empty_inventory_counts()
    entities: list[dict] = []
    if role != "cattery":
        return {"counts": counts, "entities": entities}

    if CONFIG_START_PRODUCTION_MODE == "STARTER_PACK":
        rnd = random.Random(seed)
        color = rnd.choice(CAT_TYPES)
        entities.append(
            {
                "id": f"starter-{uuid.uuid4().hex[:8]}",
                "color": color,
                "sex": "M",
                "age": 0,
                "isKitten": True,
                "hungry": False,
                "fedThisSeason": True,
            }
        )
        entities.append(
            {
                "id": f"starter-{uuid.uuid4().hex[:8]}",
                "color": color,
                "sex": "F",
                "age": 0,
                "isKitten": True,
                "hungry": False,
                "fedThisSeason": True,
            }
        )
    elif CONFIG_START_KITTENS > 0:
        rnd = random.Random(seed)
        for idx in range(CONFIG_START_KITTENS):
            entities.append(
                {
                    "id": f"start-{idx}-{uuid.uuid4().hex[:8]}",
                    "color": rnd.choice(CAT_TYPES),
                    "sex": rnd.choice(CAT_SEXES),
                    "age": 0,
                    "isKitten": True,
                    "hungry": False,
                    "fedThisSeason": True,
                }
            )
    return {"counts": counts, "entities": entities}


def _get_latest_season(db: Session, session_id: str, season_number: int) -> Season | None:
    return (
        db.query(Season)
        .filter(Season.session_id == session_id, Season.season_number == season_number)
        .order_by(Season.started_at.desc(), Season.id.desc())
        .first()
    )

def start_game_session(db: Session, user_id: str) -> GameSession:
    if CONFIG_ROLE_PLAYER == "random":
        role = random.choice(["cattery", "petshop"])
    else:
        role = CONFIG_ROLE_PLAYER

    start_inventory = _build_start_inventory_for_player(role=role, seed=f"{user_id}:{datetime.utcnow().isoformat()}")
    now = datetime.utcnow()
    session = GameSession(
        user_id=user_id,
        assigned_role=role,
        status="active",
        inventory_json=_serialize_inventory(start_inventory),
        last_action_at=now,
        inactive_timeout_at=now + timedelta(minutes=5),
    )
    db.add(session)
    db.flush()

    season1 = Season(
        session_id=session.id,
        season_number=1,
        coins_start=START_COINS,
        coins_end=START_COINS,
        profit=0,
        bot_coins_end=START_COINS,
    )
    db.add(season1)
    ensure_competitors_for_session(db, session)
    db.commit()
    db.refresh(session)
    return session

def add_event(db: Session, session_id: str, season_number: int, event_type: str, payload: dict):
    ev = GameEvent(
        session_id=session_id,
        season_number=season_number,
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    db.add(ev)
    db.commit()

def _bot_step(bot_coins: int, season_number: int) -> int:
    # очень простой бот для MVP: иногда зарабатывает, иногда тратит
    # имитируем "ограниченность" бота: не уходит в минус
    delta = random.choice([0, 1, 2, 3, -1, -2])
    new_coins = max(0, bot_coins + delta)
    return new_coins

def finish_season(
    db: Session,
    session_id: str,
    season_number: int,
    finish_early: bool,
    nursery: dict | None = None,
    nursery_coins_delta: int | None = None,
) -> tuple[Season, Season | None, dict[str, object]]:
    session = db.get(GameSession, session_id)
    season = _get_latest_season(db, session_id, season_number)
    if not season:
        raise ValueError("invalid_season")

    # Повторный финиш того же сезона не должен повторно применять экономику и создавать дубли.
    if season.ended_at:
        next_season = _get_latest_season(db, session_id, season_number + 1) if season_number < SEASONS_TOTAL else None
        return season, next_season, {
            "escapedCount": 0,
            "escapedCatIds": [],
            "escapedAnimals": [],
        }

    coins_start = season.coins_start
    backend_coins_end, meta = apply_economy_events(db, session, season_number, coins_start)
    progress = get_game_progress(db, session_id, season_number)
    applied_nursery_coins_delta = (
        _safe_int(nursery_coins_delta, 0)
        if nursery_coins_delta is not None
        else _safe_int(progress.nursery_coins_delta, 0) if progress else 0
    )
    coins_end = max(0, int(backend_coins_end) + int(applied_nursery_coins_delta))
    meta["finishEarly"] = bool(finish_early)
    meta["backendCoinsEnd"] = int(backend_coins_end)
    meta["nurseryCoinsDeltaApplied"] = int(applied_nursery_coins_delta)
    meta["effectiveCoinsEnd"] = int(coins_end)
    escape_transition = _apply_nursery_escape_transition(
        session,
        nursery,
        adult_age=ADULT_AGE,
    )
    meta["escapedCats"] = int(escape_transition.get("escapedCount", 0) or 0)
    meta["escapedCatIds"] = list(escape_transition.get("escapedCatIds") or [])

    season.meta_json = json.dumps(meta, ensure_ascii=False)
    
    # AI-конкуренты питомников: берем лучший бот-результат по монетам в текущем сезоне.
    advance_competitors_for_season(db, session_id=session_id, season_number=season_number)
    top_bot = (
        db.query(CatteryCompetitor)
        .filter(
            CatteryCompetitor.session_id == session_id,
            CatteryCompetitor.is_bot.is_(True),
            CatteryCompetitor.season_number >= season_number,
        )
        .order_by(CatteryCompetitor.coins.desc())
        .first()
    )
    bot_end = int(top_bot.coins) if top_bot else _bot_step(season.bot_coins_end, season_number)

    season.coins_end = coins_end
    season.profit = coins_end - coins_start
    season.bot_coins_end = bot_end
    season.ended_at = datetime.utcnow()
    
    next_season = None
    if coins_end > 0 and season_number < SEASONS_TOTAL:
        next_num = season_number + 1
        next_season = _get_latest_season(db, session_id, next_num)
        if not next_season:
            next_season = Season(
                session_id=session_id,
                season_number=next_num,
                coins_start=coins_end,
                coins_end=coins_end,
                profit=0,
                bot_coins_end=bot_end,
            )
            db.add(next_season)
        advance_competitors_for_season(db, session_id=session_id, season_number=next_num)

    db.commit()
    db.refresh(season)
    if next_season:
        db.refresh(next_season)

    add_event(db, session_id, season_number, "season_summary", meta)

    return season, next_season, escape_transition


def finish_session(db: Session, session_id: str) -> GameSession:
    session = db.get(GameSession, session_id)

    last_season = db.query(Season).filter(Season.session_id == session_id).order_by(Season.season_number.desc()).first()
    session.status = "finished"
    session.finished_at = datetime.utcnow()
    session.result_coins_player = last_season.coins_end if last_season else START_COINS
    session.result_coins_bot = last_season.bot_coins_end if last_season else START_COINS

    db.commit()
    db.refresh(session)
    return session

def compute_competencies(db: Session, session_id: str) -> list[dict]:
    session = db.get(GameSession, session_id)
    seasons = (
        db.query(Season)
        .filter(Season.session_id == session_id)
        .order_by(Season.season_number.asc())
        .all()
    )

    player_end = session.result_coins_player
    bot_end = session.result_coins_bot

    # --- агрегируем meta по сезонам ---
    metas = []
    profits = []
    for s in seasons:
        try:
            m = json.loads(s.meta_json or "{}")
        except Exception:
            m = {}
        metas.append(m)
        profits.append(float(s.profit or 0))

    def msum(key: str) -> float:
        return float(sum((m.get(key, 0) or 0) for m in metas))

    trade_profit_total = msum("tradeProfit")
    credits_taken = msum("creditsTaken")
    credits_repaid = msum("creditsRepaid")
    interest_paid = msum("interestPaid")
    utility_paid = msum("utilityPaid")


    finish_early_cnt = sum(1 for m in metas if m.get("finishEarly"))


    debt_end_last = 0.0
    if metas:
        debt_end_last = float(metas[-1].get("debtEnd", 0) or 0)

    seasons_cnt = max(1, len(seasons))
    m_disc = 1.0 - min(1.0, finish_early_cnt / seasons_cnt)
    discipline_score = round(m_disc * 100)
    avg_profit = sum(profits) / seasons_cnt
    profitable_seasons = sum(1 for p in profits if p > 0)

    # --- 1) RESULT: победа над ботом ---
    m_result = max(0.0, min(1.0, (player_end - bot_end + 40) / 80))
    result_score = round(m_result * 100)

    # --- 2) PROFITABILITY: прибыльность (средняя прибыль + доля прибыльных сезонов) ---
    target_avg_profit = 2.0
    m_avg = max(0.0, min(1.0, avg_profit / target_avg_profit))
    m_share = profitable_seasons / seasons_cnt
    profitability_score = round((0.6 * m_avg + 0.4 * m_share) * 100)

    # --- 3) FINANCIAL DISCIPLINE: работа с кредитами/процентами ---
    # штрафуем за проценты и большой долг к концу игры
    # (в дипломе логика понятная: дешевле долг -> выше дисциплина)
    # нормируем проценты: 0..5 монет за сезон * seasons_cnt
    norm_interest = max(1.0, 5.0 * seasons_cnt)
    m_interest = 1.0 - max(0.0, min(1.0, interest_paid / norm_interest))
    # нормируем долг: 0..35 (по ТЗ)
    m_debt = 1.0 - max(0.0, min(1.0, debt_end_last / 35.0))
    financial_discipline_score = round((0.7 * m_interest + 0.3 * m_debt) * 100)

    # --- 4) COST CONTROL: контроль расходов (коммуналка + проценты относительно бюджета) ---
    total_costs = utility_paid + interest_paid

    # бюджет = сумма coins_start по сезонам (или просто START_COINS * seasons_cnt)
    budget = float(sum((s.coins_start or 0) for s in seasons))
    budget = max(1.0, budget)

    m_cost = 1.0 - max(0.0, min(1.0, total_costs / budget))
    cost_control_score = round(m_cost * 100)

    # --- 5) DEBT MANAGEMENT: управление долгом (брал vs вернул, долг на финише) ---
    # если много взял и мало вернул + остался долг -> ниже
    repay_ratio = 1.0
    if credits_taken > 0:
        repay_ratio = max(0.0, min(1.0, credits_repaid / credits_taken))
    m_repay = repay_ratio
    m_debt2 = 1.0 - max(0.0, min(1.0, debt_end_last / 35.0))
    debt_management_score = round((0.6 * m_repay + 0.4 * m_debt2) * 100)

    # --- сохраняем в БД как раньше (code/score/explain_json) ---
    db_items = [
        {"code": "RESULT", "score": result_score, "explain": [f"Итог: игрок {player_end}, бот {bot_end}"]},
        {"code": "PROFITABILITY", "score": profitability_score, "explain": [f"Средняя прибыль: {avg_profit:.2f}", f"Плюсовых сезонов: {profitable_seasons}/{seasons_cnt}"]},
        {"code": "FIN_DISCIPLINE", "score": financial_discipline_score, "explain": [f"Проценты: {interest_paid:.2f}", f"Долг на конец: {debt_end_last:.2f}"]},
        {"code": "COST_CONTROL", "score": cost_control_score, "explain": [f"Коммуналка: {utility_paid:.2f}", f"Проценты: {interest_paid:.2f}"]},
        {"code": "DEBT_MGMT", "score": debt_management_score, "explain": [f"Взято кредитов: {credits_taken:.2f}", f"Возвращено: {credits_repaid:.2f}", f"Долг на конец: {debt_end_last:.2f}"]},
    ]

    db.query(CompetencyResult).filter(CompetencyResult.session_id == session_id).delete()
    for item in db_items:
        db.add(
            CompetencyResult(
                session_id=session_id,
                competency_code=item["code"],
                score=item["score"],
                explain_json=json.dumps(item["explain"], ensure_ascii=False),
            )
        )
    db.commit()

    # --- API-формат ---
    api_items = [
        {
            "name": "Result (победа над ботом)",
            "score": result_score,
            "evidence": {"playerCoins": player_end, "botCoins": bot_end},
            "explanation": "Сравнение итоговых монет игрока и бота."
        },
        {
            "name": "Profitability (прибыльность)",
            "score": profitability_score,
            "evidence": {"avgProfit": round(avg_profit, 2), "profitableSeasons": profitable_seasons, "seasons": seasons_cnt},
            "explanation": "Оценивает, насколько стабильно игрок выходит в плюс и какая средняя прибыль по сезонам."
        },
        {
            "name": "Discipline (дисциплина по времени)",
            "score": discipline_score,
            "evidence": {"finishEarlySeasons": finish_early_cnt, "seasons": seasons_cnt},
            "explanation": "Штрафуется досрочное завершение сезонов: чем чаще — тем ниже дисциплина."
        },
        {
            "name": "Financial Discipline (проценты и долг)",
            "score": financial_discipline_score,
            "evidence": {"interestPaid": round(interest_paid, 2), "debtEnd": round(debt_end_last, 2)},
            "explanation": "Чем меньше процентов и остаточного долга, тем выше оценка финансовой дисциплины."
        },
        {
            "name": "Cost Control (контроль расходов)",
            "score": cost_control_score,
            "evidence": {"utilityPaid": round(utility_paid, 2), "interestPaid": round(interest_paid, 2), "tradeProfit": round(trade_profit_total, 2)},
            "explanation": "Сравнивает операционные расходы (коммуналка+проценты) с результатом торговли."
        },
        {
            "name": "Debt Management (управление кредитами)",
            "score": debt_management_score,
            "evidence": {"creditsTaken": round(credits_taken, 2), "creditsRepaid": round(credits_repaid, 2), "debtEnd": round(debt_end_last, 2)},
            "explanation": "Оценивает, насколько игрок возвращает кредиты и не оставляет долг к концу игры."
        },
    ]

    return api_items


def _weighted_rate(old_debt: int, old_rate: float, add_amount: int, add_rate: float) -> float:
    total = old_debt + add_amount
    if total <= 0:
        return 0.0
    return (old_debt * old_rate + add_amount * add_rate) / total


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_color(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized == "orange":
        normalized = "ginger"
    return normalized if normalized in CAT_TYPES else None


def _normalize_sex(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    return normalized if normalized in CAT_SEXES else None


def _normalize_counterparty_type(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if normalized in COUNTERPARTY_TYPES else None


def _empty_inventory_counts() -> dict:
    return {color: {sex: 0 for sex in CAT_SEXES} for color in CAT_TYPES}


def _aggregate_inventory_counts(counts: dict) -> dict:
    return {color: int(counts.get(color, {}).get("M", 0) + counts.get(color, {}).get("F", 0)) for color in CAT_TYPES}


def apply_economy_events(db: Session, session: GameSession, season_number: int, coins: int) -> tuple[int, dict]:
    """
    Применяет к балансу события текущего сезона:
    - trade_buy / trade_sell
    - credit_taken / credit_repaid
    Возвращает: (новые_монеты, метаданные_сезона)
    """
    events = db.query(GameEvent).filter(
        and_(GameEvent.session_id == session.id, GameEvent.season_number == season_number)
    ).order_by(GameEvent.created_at.asc()).all()

    meta = {
        "tradeProfit": 0,
        "tradeSellTotal": 0,
        "tradeBuyTotal": 0,
        "creditsTaken": 0,
        "creditsRepaid": 0,
        "interestPaid": 0,
        "utilityPaid": 0,
        "debtStart": session.debt_total,
        "debtEnd": session.debt_total,
    }

    for ev in events:
        try:
            payload = json.loads(ev.payload_json or "{}")
        except Exception:
            payload = {}

        if ev.event_type == "trade_buy":
            # payload: { qty, price }
            qty = int(payload.get("qty", 0))
            price = int(payload.get("price", 0))
            cost = max(0, qty * price)
            coins = max(0, coins - cost)
            meta["tradeProfit"] -= cost
            meta["tradeBuyTotal"] += cost

        elif ev.event_type == "trade_sell":
            qty = int(payload.get("qty", 0))
            price = int(payload.get("price", 0))
            income = max(0, qty * price)
            coins = coins + income
            meta["tradeProfit"] += income
            meta["tradeSellTotal"] += income

        elif ev.event_type == "credit_taken":
            # payload: { creditType, amount }
            amount = int(payload.get("amount", 0))
            credit_type = payload.get("creditType", "consumer")
            rate = CREDIT_RATES.get(credit_type, 0.05)

            # лимит по сумме кредита
            available = max(0, CREDIT_MAX - session.debt_total)
            take = max(0, min(amount, available))

            coins += take
            session.debt_rate = _weighted_rate(session.debt_total, session.debt_rate, take, rate)
            session.debt_total += take
            meta["creditsTaken"] += take

        elif ev.event_type == "credit_repaid":
            amount = int(payload.get("amount", 0))
            pay = max(0, min(amount, session.debt_total, coins))
            coins -= pay
            session.debt_total -= pay
            meta["creditsRepaid"] += pay
            if session.debt_total == 0:
                session.debt_rate = 0.0

        elif ev.event_type == "trade_market":
            action = payload.get("action")
            cat_type = _normalize_color(payload.get("catType"))
            qty = _safe_int(payload.get("qty"), 0)
            unit_price = _trade_event_unit_price(session.id, season_number, payload, action_fallback=action)
            if cat_type not in CAT_TYPES or qty <= 0 or unit_price <= 0:
                continue

            if action == "buy":
                cost = qty * unit_price
                coins = max(0, coins - cost)
                meta["tradeProfit"] -= cost
                meta["tradeBuyTotal"] = meta.get("tradeBuyTotal", 0) + cost

            elif action == "sell":
                income = qty * unit_price
                coins = coins + income
                meta["tradeProfit"] += income
                meta["tradeSellTotal"] = meta.get("tradeSellTotal", 0) + income


    
    
    # коммуналка (обязательный расход сезона)
    utility = 3 if session.assigned_role == "cattery" else 1
    coins = max(0, coins - utility)
    meta["utilityPaid"] = meta.get("utilityPaid", 0) + utility
    meta["debtEnd"] = session.debt_total
    return coins, meta

def generate_market_prices(
    session_id: str,
    season_number: int,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    """
    Детерминированная генерация цен с учетом контрагента:
    один и тот же магазин/питомник в том же сезоне всегда даст одинаковые цены.
    """
    cp_type = _normalize_counterparty_type(counterparty_type) or "market"
    cp_id = _safe_int(counterparty_id, 0)
    seed = f"{session_id}:{season_number}:{cp_type}:{cp_id}"
    rnd = random.Random(seed)

    market: dict[str, dict] = {}
    for color in CAT_TYPES:
        by_sex: dict[str, dict] = {}
        buy_values: list[int] = []
        sell_values: list[int] = []
        for sex in CAT_SEXES:
            base_buy = rnd.randint(2, 10)
            margin = rnd.randint(1, 5)
            # Небольшой смещающий коэффициент по полу, чтобы цены отличались.
            sex_shift = 1 if (sex == "F" and rnd.random() > 0.5) else 0
            buy = max(1, base_buy + sex_shift)
            sell = max(buy + 1, buy + margin)
            by_sex[sex] = {"buy": buy, "sell": sell}
            buy_values.append(buy)
            sell_values.append(sell)

        market[color] = {
            "buy": round(sum(buy_values) / len(buy_values)),
            "sell": round(sum(sell_values) / len(sell_values)),
            **by_sex,
        }
    return market


def get_market(
    session_id: str,
    season_number: int,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    return generate_market_prices(session_id, season_number, counterparty_type, counterparty_id)


def _market_variant_price(market: dict, color: str, sex: str | None, side: str) -> int:
    entry = market.get(color, {})
    normalized_sex = _normalize_sex(sex)
    if normalized_sex and isinstance(entry.get(normalized_sex), dict):
        return max(0, _safe_int(entry[normalized_sex].get(side), 0))
    return max(0, _safe_int(entry.get(side), 0))


def _trade_event_unit_price(
    session_id: str,
    season_number: int,
    payload: dict,
    action_fallback: str | None = None,
) -> int:
    action = payload.get("action") or action_fallback
    cat_type = _normalize_color(payload.get("catType"))
    cat_sex = _normalize_sex(payload.get("catSex"))
    counterparty_type = _normalize_counterparty_type(payload.get("counterpartyType"))
    counterparty_id = payload.get("counterpartyId")

    explicit_price = _safe_int(payload.get("unitPrice"), 0)
    if explicit_price > 0:
        return explicit_price

    if action not in {"buy", "sell"} or not cat_type:
        return 0

    market = generate_market_prices(
        session_id=session_id,
        season_number=season_number,
        counterparty_type=counterparty_type,
        counterparty_id=counterparty_id,
    )
    side = "buy" if action == "buy" else "sell"
    return _market_variant_price(market, cat_type, cat_sex, side)


def _normalize_entity(entity: dict) -> dict | None:
    color = _normalize_color(entity.get("color") or entity.get("catType"))
    sex = _normalize_sex(entity.get("sex") or entity.get("catSex"))
    if not color or not sex:
        return None

    age_raw = entity.get("age", entity.get("ageSeasons"))
    age = max(0, _safe_int(age_raw, 0))
    explicit_kitten = entity.get("isKitten")
    if age_raw is not None:
        is_kitten = age < ADULT_AGE
    elif isinstance(explicit_kitten, bool):
        is_kitten = explicit_kitten
    else:
        is_kitten = age < ADULT_AGE
    return {
        "id": str(entity.get("id") or f"inv-{uuid.uuid4().hex[:12]}"),
        "color": color,
        "sex": sex,
        "age": age,
        "isKitten": is_kitten,
        "hungry": bool(entity.get("hungry", False)),
        "fedThisSeason": bool(entity.get("fedThisSeason", False)),
    }


def _normalize_nursery_snapshot(nursery: dict | None) -> dict:
    if not isinstance(nursery, dict):
        return {}
    home = nursery.get("home") if isinstance(nursery.get("home"), dict) else {}
    return {
        "hasHome": bool(nursery.get("hasHome")),
        "cats": [cat for cat in (nursery.get("cats") or []) if isinstance(cat, dict)],
        "home": {
            "parents": {
                "left": list((home.get("parents") or {}).get("left") or [None, None]),
                "right": list((home.get("parents") or {}).get("right") or [None, None]),
            },
            "kittens": [cat if isinstance(cat, dict) else None for cat in (home.get("kittens") or [])],
        },
    }


def _apply_nursery_escape_transition(
    session: GameSession,
    nursery: dict | None,
    *,
    adult_age: int = ADULT_AGE,
) -> dict[str, object]:
    if not isinstance(nursery, dict) or not nursery or (
        not nursery.get("cats") and not nursery.get("home")
    ):
        return {
            "escapedCount": 0,
            "escapedCatIds": [],
            "escapedAnimals": [],
        }
    normalized_nursery = _normalize_nursery_snapshot(nursery)
    inventory = _parse_inventory(session.inventory_json or "{}")
    current_entities = inventory.get("entities", [])
    if not current_entities:
        return {
            "escapedCount": 0,
            "escapedCatIds": [],
            "escapedAnimals": [],
        }

    current_by_id = {
        str(entity.get("id")): entity
        for entity in current_entities
        if entity.get("id") is not None
    }
    snapshot_entities: dict[str, dict] = {}
    for cat in normalized_nursery.get("cats", []):
        normalized = _normalize_entity(cat)
        if normalized:
            snapshot_entities[normalized["id"]] = normalized
    for cat in normalized_nursery.get("home", {}).get("kittens", []):
        normalized = _normalize_entity(cat) if isinstance(cat, dict) else None
        if normalized:
            snapshot_entities[normalized["id"]] = normalized

    safe_ids: set[str] = set()
    if normalized_nursery.get("hasHome"):
        parents = normalized_nursery.get("home", {}).get("parents", {})
        for side in ("left", "right"):
            for cat_id in parents.get(side, []):
                if cat_id is not None:
                    safe_ids.add(str(cat_id))
        for kitten in normalized_nursery.get("home", {}).get("kittens", []):
            if isinstance(kitten, dict) and kitten.get("id") is not None:
                safe_ids.add(str(kitten["id"]))

    survivor_entities: list[dict] = []
    escaped_entities: list[dict] = []
    for entity_id, current_entity in current_by_id.items():
        snapshot = snapshot_entities.get(entity_id) or current_entity
        if entity_id not in safe_ids:
            escaped_entities.append(
                {
                    **snapshot,
                    "id": entity_id,
                    "status": "ESCAPED",
                    "isEscaped": True,
                }
            )
            continue

        next_age = max(0, _safe_int(snapshot.get("age", current_entity.get("age", 0)), 0)) + 1
        survivor_entities.append(
            {
                **current_entity,
                "id": entity_id,
                "color": _normalize_color(snapshot.get("color") or current_entity.get("color")) or current_entity.get("color"),
                "sex": _normalize_sex(snapshot.get("sex") or current_entity.get("sex")) or current_entity.get("sex"),
                "age": next_age,
                "isKitten": next_age < adult_age,
                "hungry": True,
                "fedThisSeason": False,
            }
        )

    session.inventory_json = _serialize_inventory(
        {
            "counts": _empty_inventory_counts(),
            "entities": survivor_entities,
        }
    )
    return {
        "escapedCount": len(escaped_entities),
        "escapedCatIds": [str(entity.get("id")) for entity in escaped_entities if entity.get("id") is not None],
        "escapedAnimals": escaped_entities,
    }


def _parse_inventory(inv_json: str) -> dict:
    try:
        raw = json.loads(inv_json or "{}")
    except Exception:
        raw = {}

    counts = _empty_inventory_counts()
    entities: list[dict] = []

    if isinstance(raw, dict):
        raw_counts = raw.get("counts") if isinstance(raw.get("counts"), dict) else raw
        if isinstance(raw_counts, dict):
            for color in CAT_TYPES:
                color_value = raw_counts.get(color)
                if isinstance(color_value, dict):
                    counts[color]["M"] = max(0, _safe_int(color_value.get("M"), 0))
                    counts[color]["F"] = max(0, _safe_int(color_value.get("F"), 0))
                else:
                    total = max(0, _safe_int(color_value, 0))
                    counts[color]["M"] = total
                    counts[color]["F"] = 0

        raw_entities = raw.get("entities")
        if isinstance(raw_entities, list):
            for item in raw_entities:
                if not isinstance(item, dict):
                    continue
                normalized = _normalize_entity(item)
                if normalized:
                    entities.append(normalized)

    # Если есть entities, делаем counts по факту entities (authoritative).
    if entities:
        counts = _empty_inventory_counts()
        for entity in entities:
            counts[entity["color"]][entity["sex"]] += 1

    return {"counts": counts, "entities": entities}


def _serialize_inventory(data: dict) -> str:
    return json.dumps({"counts": data.get("counts", _empty_inventory_counts()), "entities": data.get("entities", [])}, ensure_ascii=False)


def get_inventory_view(inv_json: str) -> tuple[dict, list[dict]]:
    parsed = _parse_inventory(inv_json)
    return _aggregate_inventory_counts(parsed["counts"]), parsed["entities"]


def _estimate_trade_coins(db: Session, session_id: str, season_number: int, base_coins: int) -> int:
    """
    Оцениваем доступные монеты, применяя только trade_market события сезона.
    Кредитные/прочие события не учитываем здесь, чтобы не мутировать сессию.
    """
    events = (
        db.query(GameEvent)
        .filter(
            and_(
                GameEvent.session_id == session_id,
                GameEvent.season_number == season_number,
                GameEvent.event_type == "trade_market",
            )
        )
        .order_by(GameEvent.created_at.asc())
        .all()
    )

    coins = int(base_coins)
    for ev in events:
        try:
            payload = json.loads(ev.payload_json or "{}")
        except Exception:
            payload = {}
        action = payload.get("action")
        cat_type = _normalize_color(payload.get("catType"))
        qty = _safe_int(payload.get("qty"), 0)
        price = _trade_event_unit_price(session_id, season_number, payload, action_fallback=action)

        if cat_type not in CAT_TYPES or qty <= 0 or price <= 0:
            continue
        if action == "buy":
            coins = max(0, coins - qty * price)
        elif action == "sell":
            coins += qty * price
    return coins


def estimate_state(db: Session, session_id: str, season_number: int) -> dict:
    season = _get_latest_season(db, session_id, season_number)
    if not season:
        return {"coins": 0, "debt_total": 0, "debt_rate": 0.0}

    events = (
        db.query(GameEvent)
        .filter(and_(GameEvent.session_id == session_id, GameEvent.season_number == season_number))
        .order_by(GameEvent.created_at.asc())
        .all()
    )

    coins = int(season.coins_start)
    debt_total = 0
    debt_rate = 0.0

    for ev in events:
        try:
            payload = json.loads(ev.payload_json or "{}")
        except Exception:
            payload = {}

        if ev.event_type == "trade_market":
            action = payload.get("action")
            cat_type = _normalize_color(payload.get("catType"))
            qty = _safe_int(payload.get("qty"), 0)
            price = _trade_event_unit_price(session_id, season_number, payload, action_fallback=action)
            if cat_type not in CAT_TYPES or qty <= 0 or price <= 0:
                continue
            if action == "buy":
                coins = max(0, coins - qty * price)
            elif action == "sell":
                coins += qty * price

        elif ev.event_type == "credit_taken":
            amount = _safe_int(payload.get("amount"), 0)
            credit_type = payload.get("creditType", "consumer")
            rate = CREDIT_RATES.get(credit_type, 0.05)

            available = max(0, CREDIT_MAX - debt_total)
            take = max(0, min(amount, available))
            coins += take
            debt_rate = _weighted_rate(debt_total, debt_rate, take, rate)
            debt_total += take

        elif ev.event_type == "credit_repaid":
            amount = _safe_int(payload.get("amount"), 0)
            pay = max(0, min(amount, debt_total, coins))
            coins -= pay
            debt_total -= pay
            if debt_total == 0:
                debt_rate = 0.0

    return {"coins": coins, "debt_total": debt_total, "debt_rate": debt_rate}


def _take_from_counts(counts: dict, color: str, sex: str | None, qty: int) -> bool:
    if qty <= 0:
        return False
    normalized_sex = _normalize_sex(sex)
    if normalized_sex:
        if counts[color][normalized_sex] < qty:
            return False
        counts[color][normalized_sex] -= qty
        return True

    available = counts[color]["M"] + counts[color]["F"]
    if available < qty:
        return False
    # Списываем сначала M, затем F, чтобы поведение было детерминированным.
    take_m = min(counts[color]["M"], qty)
    counts[color]["M"] -= take_m
    counts[color]["F"] -= (qty - take_m)
    return True


def _remove_entities(entities: list[dict], color: str, sex: str | None, qty: int) -> list[dict]:
    if qty <= 0 or not entities:
        return entities
    normalized_sex = _normalize_sex(sex)
    to_remove = qty
    next_entities = []
    for entity in entities:
        same_color = _normalize_color(entity.get("color")) == color
        same_sex = _normalize_sex(entity.get("sex")) == normalized_sex if normalized_sex else True
        if to_remove > 0 and same_color and same_sex:
            to_remove -= 1
            continue
        next_entities.append(entity)
    return next_entities


def _remove_entity_by_id(entities: list[dict], entity_id: str | None, color: str, sex: str | None) -> tuple[list[dict], bool]:
    if not entities or not entity_id:
        return entities, False
    normalized_sex = _normalize_sex(sex)
    removed = False
    next_entities = []
    for entity in entities:
        if removed:
            next_entities.append(entity)
            continue
        same_id = str(entity.get("id")) == str(entity_id)
        same_color = _normalize_color(entity.get("color")) == color
        same_sex = _normalize_sex(entity.get("sex")) == normalized_sex if normalized_sex else True
        if same_id and same_color and same_sex:
            removed = True
            continue
        next_entities.append(entity)
    return next_entities, removed


def _append_entities(entities: list[dict], color: str, sex: str, qty: int, first_entity_id: str | None = None) -> list[dict]:
    next_entities = list(entities or [])
    for idx in range(max(0, qty)):
        provided_id = first_entity_id if idx == 0 and first_entity_id else None
        next_entities.append(
            {
                "id": provided_id or f"inv-{uuid.uuid4().hex[:12]}",
                "color": color,
                "sex": sex,
                "age": 0,
                "isKitten": True,
                "hungry": False,
                "fedThisSeason": True,
            }
        )
    return next_entities


def trade_market(
    db: Session,
    session: GameSession,
    season_number: int,
    action: str,
    cat_type: str,
    qty: int,
    cat_sex: str | None = None,
    entity_id: str | None = None,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> tuple[bool, str | None]:
    color = _normalize_color(cat_type)
    sex = _normalize_sex(cat_sex)
    cp_type = _normalize_counterparty_type(counterparty_type)

    if action not in {"buy", "sell"}:
        return False, "invalid_action"
    if color not in CAT_TYPES:
        return False, "invalid_cat_type"
    if qty <= 0:
        return False, "invalid_qty"
    if cp_type is None:
        return False, "invalid_counterparty_type"
    if sex is None:
        return False, "invalid_cat_sex"
    if session.assigned_role == "cattery" and cp_type != "shop":
        return False, "invalid_counterparty_for_role"

    season = _get_latest_season(db, session.id, season_number)
    if not season:
        return False, "invalid_season"

    inventory_data = _parse_inventory(session.inventory_json)
    counts = inventory_data["counts"]
    entities = inventory_data["entities"]

    market = generate_market_prices(
        session.id,
        season_number,
        counterparty_type=cp_type,
        counterparty_id=counterparty_id,
    )

    if action == "sell":
        if entity_id:
            entities, removed = _remove_entity_by_id(entities, entity_id, color, sex)
            if not removed:
                return False, "not_enough_inventory"
            counts = _empty_inventory_counts()
            for entity in entities:
                counts[entity["color"]][entity["sex"]] += 1
        else:
            if not _take_from_counts(counts, color, sex, qty):
                return False, "not_enough_inventory"
            entities = _remove_entities(entities, color, sex, qty)
        unit_price = _market_variant_price(market, color, sex, "sell")
    else:
        unit_price = _market_variant_price(market, color, sex, "buy")
        if unit_price <= 0:
            return False, "invalid_market_price"
        cost = qty * unit_price
        available = _estimate_trade_coins(db, session.id, season_number, season.coins_end)
        if available < cost:
            return False, "not_enough_coins"
        counts[color][sex] += qty
        entities = _append_entities(entities, color, sex, qty, first_entity_id=entity_id)

    session.inventory_json = _serialize_inventory({"counts": counts, "entities": entities})
    ev_payload = {
        "action": action,
        "catType": color,
        "catSex": sex,
        "entityId": entity_id,
        "qty": qty,
        "unitPrice": unit_price,
        "counterpartyType": cp_type,
        "counterpartyId": _safe_int(counterparty_id, 0),
    }
    ev = GameEvent(
        session_id=session.id,
        season_number=season_number,
        event_type="trade_market",
        payload_json=json.dumps(ev_payload, ensure_ascii=False),
    )
    db.add(ev)
    db.commit()
    db.refresh(session)
    return True, None


def get_game_progress(db: Session, session_id: str, season_number: int) -> GameProgress | None:
    return (
        db.query(GameProgress)
        .filter(
            GameProgress.session_id == session_id,
            GameProgress.season_number == season_number,
        )
        .order_by(GameProgress.updated_at.desc(), GameProgress.id.desc())
        .first()
    )


def delete_game_progress(db: Session, session_id: str) -> None:
    (
        db.query(GameProgress)
        .filter(GameProgress.session_id == session_id)
        .delete(synchronize_session=False)
    )


def save_game_progress(
    db: Session,
    session_id: str,
    season_number: int,
    nursery: dict | None,
    nursery_coins_delta: int,
    time_left: int,
) -> GameProgress:
    progress = get_game_progress(db, session_id, season_number)
    if not progress:
        progress = GameProgress(
            session_id=session_id,
            season_number=season_number,
        )
        db.add(progress)

    try:
        nursery_json = json.dumps(nursery if isinstance(nursery, dict) else {}, ensure_ascii=False)
    except Exception:
        nursery_json = "{}"

    progress.nursery_json = nursery_json
    progress.nursery_coins_delta = _safe_int(nursery_coins_delta, 0)
    progress.time_left = max(0, _safe_int(time_left, 0))
    progress.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)
    return progress
