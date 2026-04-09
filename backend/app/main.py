import asyncio
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .db import Base, engine, ensure_auth_columns, ensure_platform_columns
from .deps import (
    get_client_ip,
    get_current_active_user,
    get_db,
    get_optional_user,
    get_user_agent,
    get_ws_current_user,
)
from . import crud
from .auth_schemas import (
    AvatarOut,
    ChangePasswordIn,
    CompetenciesSummaryOut,
    AuthEmailResendIn,
    AuthLoginIn,
    AuthOkOut,
    AuthRegisterIn,
    AuthRegisterOut,
    AuthResetConfirmIn,
    AuthResetRequestIn,
    AuthResetRequestOut,
    MeOut,
    ProfileOut,
    ProfileUpdateIn,
)
from .auth_service import (
    AuthError,
    change_password,
    confirm_password_reset,
    enforce_rate_limit,
    get_me_payload,
    login_user,
    logout_all_sessions,
    logout_session,
    refresh_session,
    register_user,
    request_password_reset,
    resend_verification_email,
    verify_email_token,
)
from .settings import settings
from .schemas import (
    CandidateProfileOut,
    CandidateProfileUpdate,
)
from .schemas import (
    GameSessionStartResponse, GameEventIn, OkResponse,
    SeasonFinishIn, SeasonFinishOut, SessionFinishIn, SessionFinishOut,
    ComputeOut, MarketOut, TradeIn, TradeOut, GameStateOut,
    CreditTakeIn, CreditRepayIn,
    GameSessionItemOut, GameSessionDetailOut, SeasonDetailOut,
    GameProgressSaveIn, GameProgressOut, GameProgressGetOut,
    TradeRequestActionIn, TradeRequestActionOut, TradeRequestListOut, TradeRequestOut, TradeRequestSendIn,
    CatteryPublicViewOut,
)
from .models import (
    CandidateProfile,
    CompetencyProgress,
    CatteryCompetitor,
    GameSession,
    GameSessionResult,
    SessionCompetencyDelta,
    TradeRequest,
)

from .schemas import SeasonStateOut
from .models import Season
from .schemas import CompetencyProfileOut
from . import models
from .generate_report import generate_competency_report
from . import trade_requests as trade_requests_service
from .trade_realtime import trade_realtime_hub
from .db import SessionLocal
from .cattery_ai import get_public_spectate_view, ensure_competitors_for_session
from .game_config import (
    CONFIG_MATCH_CATTERIES,
    CONFIG_MATCH_SHOPS,
    CONFIG_MIN_BOT_SHOPS,
    CONFIG_ROLE_PLAYER,
    CONFIG_START_COINS,
    CONFIG_START_HOUSES,
    CONFIG_START_KITTENS,
    CONFIG_START_PRODUCTION_MODE,
    ADULT_AGE,
)


Base.metadata.create_all(bind=engine)
ensure_auth_columns()
ensure_platform_columns()

app = FastAPI(title="Business Cats Lite API", version="1.0")

BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BACKEND_DIR / "uploads"
AVATARS_DIR = UPLOADS_DIR / "avatars"
AVATARS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# чтобы React локально мог ходить на API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str, refresh_max_age: int) -> None:
    response.set_cookie(
        key=settings.COOKIE_ACCESS_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        domain=settings.COOKIE_DOMAIN,
        max_age=settings.ACCESS_TTL_MINUTES * 60,
    )
    response.set_cookie(
        key=settings.COOKIE_REFRESH_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        domain=settings.COOKIE_DOMAIN,
        max_age=refresh_max_age,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.COOKIE_ACCESS_NAME,
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )
    response.delete_cookie(
        key=settings.COOKIE_REFRESH_NAME,
        path="/",
        domain=settings.COOKIE_DOMAIN,
    )


def _handle_auth_error(err: AuthError) -> None:
    detail = {"error": err.error_code, "message": err.message}
    if err.retry_after_seconds:
        detail["retryAfterSeconds"] = err.retry_after_seconds
    raise HTTPException(status_code=err.status_code, detail=detail)


COMPETENCY_META = [
    ("analytics", "Аналитика", "#5b6cff"),
    ("negotiation", "Переговоры", "#2aa9e0"),
    ("strategy", "Стратегическое управление", "#16b88a"),
]

PLACE_TO_DELTA = {
    1: 0.35,
    2: 0.20,
    3: 0.10,
    22: -0.09,
    23: -0.18,
    24: -0.32,
}

INACTIVITY_TIMEOUT = timedelta(minutes=5)
INACTIVITY_CHECK_INTERVAL_SECONDS = 30
_inactivity_task: asyncio.Task | None = None


def _to_text(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _serialize_profile(user) -> dict:
    directions: list[str] = []
    if user.directions_json:
        try:
            parsed = json.loads(user.directions_json)
            if isinstance(parsed, list):
                directions = [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            directions = []
    return {
        "firstName": user.first_name,
        "lastName": user.last_name,
        "middleName": user.middle_name,
        "birthDate": user.birth_date.date() if isinstance(user.birth_date, datetime) else user.birth_date,
        "birthPlace": user.birth_place,
        "city": user.city,
        "educationType": user.education_type,
        "educationPlace": user.education_place,
        "directions": directions,
        "university": user.university,
        "eventCode": user.event_code,
        "desiredSpecialties": user.desired_specialties,
    }


def _get_or_create_competency_progress(db: Session, user_id: str) -> CompetencyProgress:
    progress = (
        db.query(CompetencyProgress)
        .filter(CompetencyProgress.user_id == user_id)
        .one_or_none()
    )
    if progress:
        return progress
    progress = CompetencyProgress(user_id=user_id)
    db.add(progress)
    db.flush()
    return progress


def _level_progress(level: float) -> float:
    if level <= 1.0:
        return 0.0
    fract = level - int(level)
    return round(fract, 4)


def _build_competency_summary(progress: CompetencyProgress) -> dict:
    items = []
    for code, title, color in COMPETENCY_META:
        level = float(getattr(progress, f"{code}_level", 1.0) or 1.0)
        delta = float(getattr(progress, f"last_{code}_delta", 0.0) or 0.0)
        items.append(
            {
                "code": code,
                "title": title,
                "level": round(max(1.0, level), 2),
                "delta": round(delta, 2),
                "progress": _level_progress(level),
                "color": color,
            }
        )
    return {"items": items, "empty": all(abs(float(i["delta"])) < 1e-6 and float(i["level"]) <= 1.0 for i in items)}


def _resolve_place(*, player_coins: int, bot_coins: int, bankrupt: bool) -> int:
    if bankrupt:
        return 24
    spread = int(player_coins) - int(bot_coins)
    if spread >= 20:
        return 1
    if spread >= 5:
        return 2
    if spread >= 0:
        return 3
    if spread >= -10:
        return 22
    if spread >= -25:
        return 23
    return 24


def _now_utc() -> datetime:
    return datetime.utcnow()


def _is_session_active(session: GameSession) -> bool:
    return str(session.status or "").lower() in {"active", "not_started"}


def _is_session_terminal(session: GameSession) -> bool:
    return str(session.status or "").lower() in {"finished", "completed", "bankrupt_completed"}


def _touch_session_activity(session: GameSession, now: datetime | None = None) -> None:
    if not _is_session_active(session):
        return
    ts = now or _now_utc()
    session.last_action_at = ts
    session.inactive_timeout_at = ts + INACTIVITY_TIMEOUT


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _base_delta_by_place(place: int) -> float:
    return float(PLACE_TO_DELTA.get(int(place), 0.0))


def _collect_session_stats(
    db: Session,
    session: GameSession,
    *,
    final_balance_override: int | None = None,
    bankrupt_reason_override: str | None = None,
) -> dict:
    seasons = (
        db.query(Season)
        .filter(Season.session_id == session.id)
        .order_by(Season.season_number.asc())
        .all()
    )
    seasons_total = int(crud.SEASONS_TOTAL)
    seasons_completed = int(sum(1 for s in seasons if s.ended_at))
    completed_all_seasons = seasons_completed >= seasons_total

    profit_total = int(sum(int(s.profit or 0) for s in seasons))
    last_season = seasons[-1] if seasons else None
    bot_balance = int(session.result_coins_bot or (last_season.bot_coins_end if last_season else 0) or 0)
    final_balance = int(
        final_balance_override
        if final_balance_override is not None
        else (
            session.final_balance
            if session.final_balance is not None
            else (
                session.result_coins_player
                if session.result_coins_player is not None
                else (last_season.coins_end if last_season else 0)
            )
        )
    )

    trade_sell_total = 0
    trade_buy_total = 0
    for season in seasons:
        try:
            meta = json.loads(season.meta_json or "{}")
        except Exception:
            meta = {}
        trade_sell_total += int(meta.get("tradeSellTotal", 0) or 0)
        trade_buy_total += int(meta.get("tradeBuyTotal", 0) or 0)
    avg_margin = 0.0
    if trade_buy_total > 0:
        avg_margin = (trade_sell_total - trade_buy_total) / float(trade_buy_total)

    user_player_id = f"user:{session.user_id}"
    successful_deals_count = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session.id,
            or_(TradeRequest.from_player_id == user_player_id, TradeRequest.to_player_id == user_player_id),
            TradeRequest.state == "ACCEPTED",
        )
        .count()
    )
    rejected_deals_count = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session.id,
            or_(TradeRequest.from_player_id == user_player_id, TradeRequest.to_player_id == user_player_id),
            TradeRequest.state.in_(["REJECTED", "CANCELLED", "EXPIRED"]),
        )
        .count()
    )
    counter_offers_used_count = (
        db.query(TradeRequest)
        .filter(
            TradeRequest.session_id == session.id,
            TradeRequest.from_player_id == user_player_id,
            or_(TradeRequest.message_code == "COUNTER_OFFER", TradeRequest.counter_of_request_id.is_not(None)),
        )
        .count()
    )

    ended_at = session.finished_at or _now_utc()
    active_play_time_seconds = 0
    if session.started_at and ended_at >= session.started_at:
        active_play_time_seconds = int((ended_at - session.started_at).total_seconds())

    bankrupt_reason = bankrupt_reason_override or (session.bankrupt_reason or "")
    if not bankrupt_reason:
        finish_reason = str(session.finish_reason or "").upper()
        if finish_reason in {"INACTIVITY_TIMEOUT", "BANKRUPT_INACTIVITY"} or bool(session.inactive_timeout_triggered):
            bankrupt_reason = "INACTIVITY"
        elif finish_reason == "BANKRUPT_MONEY" or str(session.status or "").lower() == "bankrupt_completed" or final_balance <= 0:
            bankrupt_reason = "MONEY"
        else:
            bankrupt_reason = "NONE"
    bankrupt = bankrupt_reason in {"MONEY", "INACTIVITY"}
    inactive_timeout_triggered = bankrupt_reason == "INACTIVITY" or bool(session.inactive_timeout_triggered)

    place = int(session.final_place or 0)
    if bankrupt:
        place = 24
    elif place <= 0:
        place = _resolve_place(player_coins=final_balance, bot_coins=bot_balance, bankrupt=False)

    return {
        "finalPlace": int(place),
        "bankrupt": bool(bankrupt),
        "bankruptReason": bankrupt_reason,
        "completedAllSeasons": bool(completed_all_seasons),
        "finalBalance": int(final_balance),
        "profitTotal": int(profit_total),
        "successfulDealsCount": int(successful_deals_count),
        "rejectedDealsCount": int(rejected_deals_count),
        "counterOffersUsedCount": int(counter_offers_used_count),
        "avgMargin": float(avg_margin),
        "seasonsCompleted": int(seasons_completed),
        "seasonsTotal": int(seasons_total),
        "activePlayTimeSeconds": int(active_play_time_seconds),
        "inactiveTimeoutTriggered": bool(inactive_timeout_triggered),
        "botFinalBalance": int(bot_balance),
    }


def _compute_quality_factors(stats: dict, *, base_delta: float) -> tuple[float, float, float]:
    profit_total = float(stats.get("profitTotal", 0))
    final_balance = float(stats.get("finalBalance", 0))
    avg_margin = float(stats.get("avgMargin", 0.0))
    successful = float(stats.get("successfulDealsCount", 0))
    rejected = float(stats.get("rejectedDealsCount", 0))
    counter_used = float(stats.get("counterOffersUsedCount", 0))
    seasons_completed = float(stats.get("seasonsCompleted", 0))
    seasons_total = max(1.0, float(stats.get("seasonsTotal", 1)))
    bankrupt_reason = str(stats.get("bankruptReason", "NONE") or "NONE")
    inactive_triggered = bool(stats.get("inactiveTimeoutTriggered", False))

    profit_factor = _clamp((profit_total + 30.0) / 60.0)
    margin_factor = _clamp((avg_margin + 0.5) / 1.0)
    balance_factor = _clamp(final_balance / 60.0)
    analytics_factor = _clamp(0.45 * profit_factor + 0.35 * margin_factor + 0.20 * balance_factor)

    total_deals = successful + rejected
    deals_activity_factor = _clamp(total_deals / 8.0)
    success_rate = _clamp(successful / max(1.0, total_deals))
    counter_factor = _clamp(counter_used / 3.0)
    spam_penalty = 0.0
    if total_deals > 0 and rejected > successful * 2.0:
        spam_penalty = 0.2
    negotiation_factor = _clamp(0.35 * deals_activity_factor + 0.45 * success_rate + 0.20 * counter_factor - spam_penalty)

    completion_factor = _clamp(seasons_completed / seasons_total)
    stability_factor = 0.0 if bankrupt_reason in {"MONEY", "INACTIVITY"} else 1.0
    inactivity_factor = 0.0 if inactive_triggered else 1.0
    strategy_factor = _clamp(0.35 * completion_factor + 0.35 * stability_factor + 0.20 * inactivity_factor + 0.10 * balance_factor)

    if base_delta < 0:
        if bankrupt_reason == "MONEY":
            strategy_factor = 1.0
            analytics_factor = max(analytics_factor, 0.8)
            negotiation_factor = min(negotiation_factor, 0.5)
        if bankrupt_reason == "INACTIVITY":
            strategy_factor = 1.0
            negotiation_factor = max(negotiation_factor, 0.9)
            analytics_factor = max(0.55, min(analytics_factor, 0.75))

    return analytics_factor, negotiation_factor, strategy_factor


def _compute_session_competency_deltas(stats: dict) -> dict:
    place = int(stats.get("finalPlace", 24))
    base_delta = _base_delta_by_place(place)
    analytics_factor, negotiation_factor, strategy_factor = _compute_quality_factors(stats, base_delta=base_delta)
    analytics_delta = round(base_delta * 0.40 * analytics_factor, 2)
    negotiation_delta = round(base_delta * 0.25 * negotiation_factor, 2)
    strategy_delta = round(base_delta * 0.35 * strategy_factor, 2)
    total_delta = round(analytics_delta + negotiation_delta + strategy_delta, 2)
    return {
        "baseDelta": round(base_delta, 2),
        "analyticsDelta": analytics_delta,
        "negotiationDelta": negotiation_delta,
        "strategyDelta": strategy_delta,
        "totalDelta": total_delta,
        "analyticsFactor": round(analytics_factor, 4),
        "negotiationFactor": round(negotiation_factor, 4),
        "strategyFactor": round(strategy_factor, 4),
    }


def _sync_session_competencies(
    db: Session,
    session: GameSession,
    *,
    bankrupt_reason_override: str | None = None,
    final_balance_override: int | None = None,
) -> SessionCompetencyDelta:
    existing_delta = (
        db.query(SessionCompetencyDelta)
        .filter(SessionCompetencyDelta.session_id == session.id)
        .one_or_none()
    )
    existing_result = (
        db.query(GameSessionResult)
        .filter(GameSessionResult.session_id == session.id)
        .one_or_none()
    )
    if existing_delta and existing_result and bankrupt_reason_override is None and final_balance_override is None:
        return existing_delta

    stats = _collect_session_stats(
        db,
        session,
        final_balance_override=final_balance_override,
        bankrupt_reason_override=bankrupt_reason_override,
    )

    deltas = _compute_session_competency_deltas(stats)
    analytics_delta = float(deltas["analyticsDelta"])
    negotiation_delta = float(deltas["negotiationDelta"])
    strategy_delta = float(deltas["strategyDelta"])

    progress = _get_or_create_competency_progress(db, session.user_id)
    progress.analytics_level = max(1.0, round(float(progress.analytics_level or 1.0) + analytics_delta, 2))
    progress.negotiation_level = max(1.0, round(float(progress.negotiation_level or 1.0) + negotiation_delta, 2))
    progress.strategy_level = max(1.0, round(float(progress.strategy_level or 1.0) + strategy_delta, 2))
    progress.analytics_score = int(round((progress.analytics_level - 1.0) * 100))
    progress.negotiation_score = int(round((progress.negotiation_level - 1.0) * 100))
    progress.strategy_score = int(round((progress.strategy_level - 1.0) * 100))
    progress.last_analytics_delta = analytics_delta
    progress.last_negotiation_delta = negotiation_delta
    progress.last_strategy_delta = strategy_delta

    session.final_place = int(stats["finalPlace"])
    session.final_balance = int(stats["finalBalance"])
    session.season_count_completed = int(stats["seasonsCompleted"])
    session.bankrupt_reason = str(stats["bankruptReason"])
    if session.bankrupt_reason == "INACTIVITY":
        session.inactive_bankrupt = True
        session.inactive_timeout_triggered = True
        session.finish_reason = session.finish_reason or "BANKRUPT_INACTIVITY"
        session.status = "bankrupt_completed"
    elif session.bankrupt_reason == "MONEY":
        session.finish_reason = session.finish_reason or "BANKRUPT_MONEY"
        session.status = "bankrupt_completed"
    else:
        session.finish_reason = session.finish_reason or "SEASONS_COMPLETED"
        if str(session.status or "").lower() == "finished":
            session.status = "completed"

    if existing_delta:
        existing_delta.analytics_delta = analytics_delta
        existing_delta.negotiation_delta = negotiation_delta
        existing_delta.strategy_delta = strategy_delta
        existing_delta.place_awarded = int(stats["finalPlace"])
        row = existing_delta
    else:
        row = SessionCompetencyDelta(
            user_id=session.user_id,
            session_id=session.id,
            analytics_delta=analytics_delta,
            negotiation_delta=negotiation_delta,
            strategy_delta=strategy_delta,
            place_awarded=int(stats["finalPlace"]),
        )
        db.add(row)

    result_stats = {**stats, **deltas}
    if existing_result:
        existing_result.place = int(stats["finalPlace"])
        existing_result.final_balance = int(stats["finalBalance"])
        existing_result.bankrupt_reason = str(stats["bankruptReason"])
        existing_result.total_delta = float(deltas["totalDelta"])
        existing_result.analytics_delta = analytics_delta
        existing_result.negotiation_delta = negotiation_delta
        existing_result.strategy_delta = strategy_delta
        existing_result.ended_at = session.finished_at or _now_utc()
        existing_result.reason = session.finish_reason or "SEASONS_COMPLETED"
        existing_result.stats_json = json.dumps(result_stats, ensure_ascii=False)
    else:
        db.add(
            GameSessionResult(
                user_id=session.user_id,
                session_id=session.id,
                place=int(stats["finalPlace"]),
                final_balance=int(stats["finalBalance"]),
                bankrupt_reason=str(stats["bankruptReason"]),
                total_delta=float(deltas["totalDelta"]),
                analytics_delta=analytics_delta,
                negotiation_delta=negotiation_delta,
                strategy_delta=strategy_delta,
                ended_at=session.finished_at or _now_utc(),
                reason=session.finish_reason or "SEASONS_COMPLETED",
                stats_json=json.dumps(result_stats, ensure_ascii=False),
            )
        )

    db.flush()
    return row


def _get_latest_season_row(db: Session, session_id: str, *, ended_only: bool = False) -> Season | None:
    query = db.query(Season).filter(Season.session_id == session_id)
    if ended_only:
        query = query.filter(Season.ended_at.is_not(None))
    return (
        query
        .order_by(Season.season_number.desc(), Season.started_at.desc(), Season.id.desc())
        .first()
    )


def _season_effective_coins_end(db: Session, season: Season | None) -> int:
    if not season:
        return 0
    try:
        meta = json.loads(season.meta_json or "{}")
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}
    if meta.get("effectiveCoinsEnd") is not None:
        return max(0, int(meta.get("effectiveCoinsEnd") or 0))
    progress = crud.get_game_progress(db, season.session_id, int(season.season_number))
    if progress:
        return max(0, int(season.coins_end or 0) + int(progress.nursery_coins_delta or 0))
    return max(0, int(season.coins_end or 0))


def _clear_session_activity_markers(session: GameSession) -> None:
    session.inactive_timeout_at = None


def _build_session_leaderboard(db: Session, session: GameSession, *, limit: int = 5) -> list[dict]:
    ensure_competitors_for_session(db, session)
    competitors = (
        db.query(CatteryCompetitor)
        .filter(CatteryCompetitor.session_id == session.id)
        .order_by(CatteryCompetitor.coins.desc(), CatteryCompetitor.cattery_id.asc())
        .all()
    )
    if not competitors:
        return []

    items: list[dict] = []
    player_entry: dict | None = None
    for index, competitor in enumerate(competitors, start=1):
        entry = {
            "rank": index,
            "name": "Твой питомник" if competitor.is_player else f"Питомник #{int(competitor.cattery_id)}",
            "coins": int(competitor.coins or 0),
            "isPlayer": bool(competitor.is_player),
            "catteryId": int(competitor.cattery_id),
        }
        if competitor.is_player:
            player_entry = entry
        if len(items) < limit:
            items.append(entry)

    if player_entry and player_entry["rank"] > limit:
        items.append(player_entry)
    return items


def _session_not_active_detail(session: GameSession) -> dict:
    if _is_session_terminal(session):
        return {
            "error": "SESSION_ALREADY_FINISHED",
            "message": "Session is already finished",
        }
    return {
        "error": "SESSION_NOT_ACTIVE",
        "message": "Session is not active",
    }


def _raise_session_not_active(session: GameSession) -> None:
    raise HTTPException(status_code=409, detail=_session_not_active_detail(session))


def _finalize_bankrupt_session(
    db: Session,
    session: GameSession,
    *,
    bankrupt_reason: str,
    final_balance: int,
    bot_balance: int,
) -> bool:
    if _is_session_terminal(session):
        return False

    normalized_reason = str(bankrupt_reason or "").upper()
    if normalized_reason not in {"MONEY", "INACTIVITY"}:
        raise ValueError("invalid_bankrupt_reason")

    session.result_coins_player = max(0, int(final_balance or 0))
    session.result_coins_bot = max(0, int(bot_balance or 0))
    session.status = "bankrupt_completed"
    session.finished_at = _now_utc()
    session.final_place = 24
    session.final_balance = max(0, int(final_balance or 0))
    session.bankrupt_reason = normalized_reason
    session.finish_reason = "BANKRUPT_INACTIVITY" if normalized_reason == "INACTIVITY" else "BANKRUPT_MONEY"
    session.inactive_bankrupt = normalized_reason == "INACTIVITY"
    session.inactive_timeout_triggered = normalized_reason == "INACTIVITY"
    _clear_session_activity_markers(session)

    _sync_session_competencies(
        db,
        session,
        bankrupt_reason_override=normalized_reason,
        final_balance_override=session.final_balance,
    )
    crud.delete_game_progress(db, session.id)
    db.commit()
    db.refresh(session)
    return True


def _finalize_completed_session(db: Session, session: GameSession) -> GameSession:
    if _is_session_terminal(session) and str(session.status or "").lower() in {"completed", "finished"}:
        _clear_session_activity_markers(session)
        _sync_session_competencies(db, session)
        crud.delete_game_progress(db, session.id)
        db.commit()
        db.refresh(session)
        return session
    if _is_session_terminal(session):
        return session

    session = crud.finish_session(db, session.id)
    if int(session.result_coins_player or 0) <= 0:
        _finalize_bankrupt_session(
            db,
            session,
            bankrupt_reason="MONEY",
            final_balance=int(session.result_coins_player or 0),
            bot_balance=int(session.result_coins_bot or 0),
        )
        db.refresh(session)
        return session

    session.status = "completed"
    if not session.finish_reason:
        session.finish_reason = "SEASONS_COMPLETED"
    session.bankrupt_reason = "NONE"
    _clear_session_activity_markers(session)
    _sync_session_competencies(db, session)
    crud.delete_game_progress(db, session.id)
    db.commit()
    db.refresh(session)
    return session


def _finalize_session_by_completed_seasons_if_needed(db: Session, session: GameSession) -> bool:
    if not _is_session_active(session):
        return False

    last_ended_season = _get_latest_season_row(db, session.id, ended_only=True)
    if not last_ended_season:
        return False
    if int(last_ended_season.season_number or 0) < int(crud.SEASONS_TOTAL):
        return False

    _finalize_completed_session(db, session)
    return True


def _finalize_session_by_money_if_needed(db: Session, session: GameSession) -> bool:
    if not _is_session_active(session):
        return False

    last_ended_season = _get_latest_season_row(db, session.id, ended_only=True)
    if last_ended_season:
        final_balance = _season_effective_coins_end(db, last_ended_season)
        bot_balance = int(last_ended_season.bot_coins_end or session.result_coins_bot or 0)
    elif session.result_coins_player is not None:
        final_balance = int(session.result_coins_player or 0)
        bot_balance = int(session.result_coins_bot or 0)
    else:
        return False

    if final_balance > 0:
        return False

    return _finalize_bankrupt_session(
        db,
        session,
        bankrupt_reason="MONEY",
        final_balance=final_balance,
        bot_balance=bot_balance,
    )


def _finalize_session_by_inactivity(db: Session, session: GameSession) -> bool:
    if not _is_session_active(session):
        return False

    current_season = _get_latest_season_row(db, session.id)
    season_number = int(current_season.season_number) if current_season else 1
    estimated = crud.estimate_state(db, session.id, season_number)
    progress = crud.get_game_progress(db, session.id, season_number)
    final_balance = int(estimated.get("coins", 0)) + int(progress.nursery_coins_delta or 0) if progress else int(estimated.get("coins", 0))
    bot_balance = int(current_season.bot_coins_end if current_season else session.result_coins_bot or 0)
    return _finalize_bankrupt_session(
        db,
        session,
        bankrupt_reason="INACTIVITY",
        final_balance=max(0, final_balance),
        bot_balance=bot_balance,
    )


def _ensure_session_not_timed_out(db: Session, session: GameSession) -> None:
    if _finalize_session_by_money_if_needed(db, session):
        _raise_session_not_active(session)
    if _finalize_session_by_completed_seasons_if_needed(db, session):
        _raise_session_not_active(session)
    if not _is_session_active(session):
        _raise_session_not_active(session)
    now = _now_utc()
    if session.inactive_timeout_at and now > session.inactive_timeout_at:
        _finalize_session_by_inactivity(db, session)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "INACTIVITY_TIMEOUT",
                "message": "Session closed: inactivity more than 5 minutes",
            },
        )


def _mark_session_activity(db: Session, session: GameSession) -> None:
    _touch_session_activity(session)
    db.commit()
    db.refresh(session)


async def _inactivity_watchdog() -> None:
    while True:
        await asyncio.sleep(INACTIVITY_CHECK_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            now = _now_utc()
            timed_out_sessions = (
                db.query(GameSession)
                .filter(
                    GameSession.status.in_(["active", "not_started"]),
                    GameSession.inactive_timeout_at.is_not(None),
                    GameSession.inactive_timeout_at < now,
                )
                .all()
            )
            for session in timed_out_sessions:
                _finalize_session_by_inactivity(db, session)
        except Exception:
            db.rollback()
        finally:
            db.close()


def _session_status_for_platform(session: GameSession) -> str:
    status = str(session.status or "").lower()
    if status in {"active", "not_started"}:
        return "ACTIVE"
    if status in {"bankrupt_completed"}:
        return "BANKRUPT_COMPLETED"
    return "COMPLETED"


def _reason_completed_for_session(session: GameSession, result: GameSessionResult | None = None) -> str | None:
    status = str(session.status or "").lower()
    if status in {"active", "not_started"}:
        return None

    bankrupt_reason = str(
        session.bankrupt_reason
        or (result.bankrupt_reason if result else "")
        or ""
    ).upper()
    finish_reason = str(session.finish_reason or "").upper()

    if bankrupt_reason == "INACTIVITY" or finish_reason in {"INACTIVITY_TIMEOUT", "BANKRUPT_INACTIVITY"}:
        return "BANKRUPT_INACTIVITY"
    if bankrupt_reason == "MONEY" or finish_reason == "BANKRUPT_MONEY" or status == "bankrupt_completed":
        return "BANKRUPT_MONEY"
    return "NORMAL_COMPLETION"


@app.on_event("startup")
async def _startup_inactivity_worker() -> None:
    global _inactivity_task
    if _inactivity_task is None or _inactivity_task.done():
        _inactivity_task = asyncio.create_task(_inactivity_watchdog())


@app.on_event("shutdown")
async def _shutdown_inactivity_worker() -> None:
    global _inactivity_task
    if _inactivity_task and not _inactivity_task.done():
        _inactivity_task.cancel()
        try:
            await _inactivity_task
        except asyncio.CancelledError:
            pass
    _inactivity_task = None


@app.post("/api/auth/register", response_model=AuthRegisterOut)
def auth_register(payload: AuthRegisterIn, request: Request, db: Session = Depends(get_db)):
    try:
        result = register_user(
            db,
            email=payload.email,
            password=payload.password,
            confirm_password=payload.confirmPassword,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    return {
        "ok": True,
        "requiresEmailVerification": True,
        "devEmailPreviewUrl": result.preview_url,
    }


@app.get("/api/auth/email/verify")
def auth_verify_email(token: str, request: Request, db: Session = Depends(get_db)):
    try:
        verify_email_token(
            db,
            token=token,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    redirect_url = f"{settings.APP_BASE_URL.rstrip('/')}/login?verified=1"
    return RedirectResponse(url=redirect_url, status_code=302)


@app.post("/api/auth/email/resend", response_model=AuthRegisterOut)
def auth_email_resend(payload: AuthEmailResendIn, request: Request, db: Session = Depends(get_db)):
    try:
        result = resend_verification_email(
            db,
            email=payload.email,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    return {
        "ok": True,
        "requiresEmailVerification": True,
        "devEmailPreviewUrl": result.preview_url,
    }


@app.post("/api/auth/login", response_model=AuthOkOut)
def auth_login(payload: AuthLoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        result = login_user(
            db,
            email=payload.email,
            password=payload.password,
            remember_me=payload.rememberMe,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    _set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        refresh_max_age=result.tokens.refresh_max_age,
    )
    return {"ok": True}


@app.post("/api/auth/refresh", response_model=AuthOkOut)
def auth_refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_cookie = request.cookies.get(settings.COOKIE_REFRESH_NAME)
    try:
        tokens = refresh_session(
            db,
            refresh_token=refresh_cookie,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _clear_auth_cookies(response)
        _handle_auth_error(err)

    _set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        refresh_max_age=tokens.refresh_max_age,
    )
    return {"ok": True}


@app.post("/api/auth/logout", response_model=AuthOkOut)
def auth_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    logout_session(
        db,
        refresh_token=request.cookies.get(settings.COOKIE_REFRESH_NAME),
        user_id=user.id if user else None,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    _clear_auth_cookies(response)
    return {"ok": True}


@app.post("/api/auth/logout-all", response_model=AuthOkOut)
def auth_logout_all(request: Request, response: Response, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    logout_all_sessions(
        db,
        user_id=user.id,
        ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    _clear_auth_cookies(response)
    return {"ok": True}


@app.post("/api/auth/password/reset/request", response_model=AuthResetRequestOut)
def auth_reset_request(payload: AuthResetRequestIn, request: Request, db: Session = Depends(get_db)):
    try:
        result = request_password_reset(
            db,
            email=payload.email,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    return {
        "ok": True,
        "message": "If the email exists, we sent a link.",
        "devEmailPreviewUrl": result.preview_url,
    }


@app.post("/api/auth/password/reset/confirm", response_model=AuthOkOut)
def auth_reset_confirm(payload: AuthResetConfirmIn, request: Request, db: Session = Depends(get_db)):
    try:
        enforce_rate_limit(
            db,
            action='AUTH_RESET_CONFIRM',
            key=f"ip:{get_client_ip(request) or 'unknown'}",
            limit=5,
            window_seconds=3600,
        )
        confirm_password_reset(
            db,
            token=payload.token,
            new_password=payload.newPassword,
            confirm_password=payload.confirmPassword,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    return {"ok": True}


@app.get("/api/me", response_model=MeOut)
def auth_me(user=Depends(get_current_active_user)):
    return get_me_payload(user)


@app.get("/api/me/profile", response_model=ProfileOut)
def me_profile(user=Depends(get_current_active_user)):
    return _serialize_profile(user)


@app.patch("/api/me/profile", response_model=ProfileOut)
def me_profile_update(payload: ProfileUpdateIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    if payload.birthDate and payload.birthDate > date.today():
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": "Birth date cannot be in the future"})

    user.first_name = _to_text(payload.firstName, 120)
    user.last_name = _to_text(payload.lastName, 120)
    user.middle_name = _to_text(payload.middleName, 120)
    user.birth_date = datetime.combine(payload.birthDate, datetime.min.time()) if payload.birthDate else None
    user.birth_place = _to_text(payload.birthPlace, 200)
    user.city = _to_text(payload.city, 120)
    user.education_type = _to_text(payload.educationType, 80)
    user.education_place = _to_text(payload.educationPlace, 240)
    user.directions_json = json.dumps(payload.directions, ensure_ascii=False)
    user.university = _to_text(payload.university, 240)
    user.event_code = _to_text(payload.eventCode, 120)
    user.desired_specialties = _to_text(payload.desiredSpecialties, 4000)

    if user.first_name and user.last_name:
        user.display_name = f"{user.first_name} {user.last_name}".strip()
    db.commit()
    db.refresh(user)
    return _serialize_profile(user)


@app.post("/api/me/avatar", response_model=AvatarOut)
async def me_avatar_upload(
    file: UploadFile = File(...),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    allowed_types = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    ext = allowed_types.get((file.content_type or "").lower())
    if not ext:
        filename = (file.filename or "").lower()
        if filename.endswith(".jpeg") or filename.endswith(".jpg"):
            ext = ".jpg"
        elif filename.endswith(".png"):
            ext = ".png"
        elif filename.endswith(".webp"):
            ext = ".webp"
    if not ext:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": "Unsupported avatar format"})

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": "File is empty"})
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": "Max avatar size is 5MB"})

    for suffix in (".jpg", ".png", ".webp"):
        old_path = AVATARS_DIR / f"{user.id}{suffix}"
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    avatar_path = AVATARS_DIR / f"{user.id}{ext}"
    with open(avatar_path, "wb") as fh:
        fh.write(data)

    user.avatar_url = f"/uploads/avatars/{avatar_path.name}"
    db.commit()
    db.refresh(user)
    return {"ok": True, "avatarUrl": user.avatar_url}


@app.delete("/api/me/avatar", response_model=AvatarOut)
def me_avatar_delete(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    for suffix in (".jpg", ".png", ".webp"):
        avatar_path = AVATARS_DIR / f"{user.id}{suffix}"
        if avatar_path.exists():
            avatar_path.unlink(missing_ok=True)
    user.avatar_url = None
    db.commit()
    return {"ok": True, "avatarUrl": None}


@app.post("/api/me/change-password", response_model=AuthOkOut)
def me_change_password(payload: ChangePasswordIn, request: Request, response: Response, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        change_password(
            db,
            user=user,
            current_password=payload.currentPassword,
            new_password=payload.newPassword,
            confirm_password=payload.confirmPassword,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except AuthError as err:
        _handle_auth_error(err)
    _clear_auth_cookies(response)
    return {"ok": True}


@app.get("/api/competencies/summary", response_model=CompetenciesSummaryOut)
def competencies_summary(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    progress = _get_or_create_competency_progress(db, user.id)
    db.commit()
    return _build_competency_summary(progress)


@app.get("/api/candidate/profile", response_model=CandidateProfileOut)
def get_candidate_profile(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    profile = crud.get_profile(db, user.id)

    skills = []
    if profile and profile.skills_json:
        try:
            skills = json.loads(profile.skills_json)
        except Exception:
            skills = []

    return {
        "userId": user.id,
        "fullName": profile.full_name if profile else "",
        "city": profile.city if profile else "",
        "university": profile.university if profile else "",
        "program": profile.program if profile else "",
        "studyYear": profile.study_year if profile else 0,
        "skills": skills,
    }


@app.put("/api/candidate/profile", response_model=CandidateProfileOut)
def put_candidate_profile(
    payload: CandidateProfileUpdate,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    profile = crud.update_profile(db, user.id, payload.model_dump())
    skills = json.loads(profile.skills_json) if profile.skills_json else []
    return {
        "userId": user.id,
        "fullName": profile.full_name,
        "city": profile.city,
        "university": profile.university,
        "program": profile.program,
        "studyYear": profile.study_year,
        "skills": skills,
    }
@app.post("/api/game/session/start", response_model=GameSessionStartResponse)
def game_session_start(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = _get_latest_playable_session_for_user(db, user.id)
    if not session:
        session = crud.start_game_session(db, user.id)
    _mark_session_activity(db, session)
    role = session.assigned_role
    return {
        "sessionId": session.id,
        "assignedRole": role,
        "rules": {
            "seasonsTotal": crud.SEASONS_TOTAL,
            "startCoins": CONFIG_START_COINS,
            "utilityCost": crud.UTILITY_COST,
            "credit": {"max": crud.CREDIT_MAX, "rates": crud.CREDIT_RATES},
            "match": {
                "catteries": CONFIG_MATCH_CATTERIES,
                "shops": CONFIG_MATCH_SHOPS,
                "minBotShops": CONFIG_MIN_BOT_SHOPS,
                "rolePlayerConfig": CONFIG_ROLE_PLAYER,
            },
            "startConfig": {
                "coins": CONFIG_START_COINS,
                "kittens": CONFIG_START_KITTENS,
                "houses": CONFIG_START_HOUSES,
                "productionMode": CONFIG_START_PRODUCTION_MODE,
                "adultAge": ADULT_AGE,
            },
        },
        "season": {"number": 1, "secondsLeft": crud.SEASON_SECONDS[1], "coins": CONFIG_START_COINS},
    }


@app.post("/api/game/event", response_model=OkResponse)
def game_event(payload: GameEventIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    # проверим, что сессия принадлежит пользователю
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False}
    _ensure_session_not_timed_out(db, session)
    crud.add_event(db, payload.sessionId, payload.seasonNumber, payload.eventType, payload.payload)
    _mark_session_activity(db, session)
    return {"ok": True}


@app.get("/api/game/market/{session_id}/{season_number}", response_model=MarketOut)
def game_market(
    session_id: str,
    season_number: int,
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"sessionId": session_id, "seasonNumber": season_number, "market": {}}
    _ensure_session_not_timed_out(db, session)

    market = _market_view_for_session(
        db,
        session,
        season_number,
        counterparty_type=counterpartyType,
        counterparty_id=counterpartyId,
    )
    return {"sessionId": session_id, "seasonNumber": season_number, "market": market}


def _market_view_for_session(
    db: Session,
    session: GameSession,
    season_number: int,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    if counterparty_type == "shop" and counterparty_id is not None:
        return trade_requests_service.build_shop_market_view(
            db=db,
            session_id=session.id,
            season_number=season_number,
            viewer_player_id=trade_requests_service.user_player_id(session.user_id),
            bot_player_id=trade_requests_service.counterparty_player_id("shop", counterparty_id),
        )
    return crud.get_market(session.id, season_number, counterparty_type, counterparty_id)


def _build_game_state(
    db: Session,
    session: GameSession,
    season_number: int,
    counterparty_type: str | None = None,
    counterparty_id: int | None = None,
) -> dict:
    market = _market_view_for_session(
        db,
        session,
        season_number,
        counterparty_type=counterparty_type,
        counterparty_id=counterparty_id,
    )
    inventory, inventory_entities = crud.get_inventory_view(session.inventory_json or "{}")
    est = crud.estimate_state(db, session.id, season_number)
    return {
        "sessionId": session.id,
        "seasonNumber": season_number,
        "role": session.assigned_role,
        "adultAge": ADULT_AGE,
        "market": market,
        "inventory": inventory,
        "inventoryEntities": inventory_entities,
        "coinsNowEstimate": est["coins"],
        "debtTotal": est["debt_total"],
        "debtRate": float(est["debt_rate"]),
    }


@app.get("/api/game/state/{session_id}/{season_number}", response_model=GameStateOut)
def game_state(
    session_id: str,
    season_number: int,
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {
            "sessionId": session_id,
            "seasonNumber": season_number,
            "role": "cattery",
            "adultAge": ADULT_AGE,
            "market": {},
            "inventory": {},
            "inventoryEntities": [],
            "coinsNowEstimate": 0,
            "debtTotal": 0,
            "debtRate": 0.0,
        }
    _ensure_session_not_timed_out(db, session)

    return _build_game_state(
        db,
        session,
        season_number,
        counterparty_type=counterpartyType,
        counterparty_id=counterpartyId,
    )


@app.post("/api/game/trade", response_model=TradeOut)
def game_trade(payload: TradeIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}
    _ensure_session_not_timed_out(db, session)

    ok, err = crud.trade_market(
        db,
        session=session,
        season_number=payload.seasonNumber,
        action=payload.action,
        cat_type=payload.catType,
        qty=payload.qty,
        cat_sex=payload.catSex,
        entity_id=payload.entityId,
        counterparty_type=payload.counterpartyType,
        counterparty_id=payload.counterpartyId,
    )
    state = (
        _build_game_state(
            db,
            session,
            payload.seasonNumber,
            counterparty_type=payload.counterpartyType,
            counterparty_id=payload.counterpartyId,
        )
        if ok
        else None
    )
    if ok:
        _mark_session_activity(db, session)
    return {"ok": ok, "error": err, "state": state}


@app.post("/api/game/credit/take", response_model=TradeOut)
def game_credit_take(payload: CreditTakeIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}
    _ensure_session_not_timed_out(db, session)
    if payload.amount <= 0:
        return {"ok": False, "error": "invalid_amount", "state": None}

    crud.add_event(
        db,
        payload.sessionId,
        payload.seasonNumber,
        "credit_taken",
        {"creditType": payload.creditType, "amount": payload.amount},
    )
    state = _build_game_state(db, session, payload.seasonNumber)
    _mark_session_activity(db, session)
    return {"ok": True, "error": None, "state": state}


@app.post("/api/game/credit/repay", response_model=TradeOut)
def game_credit_repay(payload: CreditRepayIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "state": None}
    _ensure_session_not_timed_out(db, session)
    if payload.amount <= 0:
        return {"ok": False, "error": "invalid_amount", "state": None}

    crud.add_event(
        db,
        payload.sessionId,
        payload.seasonNumber,
        "credit_repaid",
        {"amount": payload.amount},
    )
    state = _build_game_state(db, session, payload.seasonNumber)
    _mark_session_activity(db, session)
    return {"ok": True, "error": None, "state": state}
    



@app.post("/api/game/season/finish", response_model=SeasonFinishOut)
def game_season_finish(payload: SeasonFinishIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"seasonResult": {"error": "invalid session"}, "nextSeason": None}
    _ensure_session_not_timed_out(db, session)

    db.refresh(session)
    season, next_season, nursery_transition = crud.finish_season(
        db,
        payload.sessionId,
        payload.seasonNumber,
        payload.finishEarly,
        nursery=payload.nursery if isinstance(payload.nursery, dict) else None,
        nursery_coins_delta=payload.nurseryCoinsDelta,
    )
    if int(season.coins_end or 0) <= 0:
        _finalize_bankrupt_session(
            db,
            session,
            bankrupt_reason="MONEY",
            final_balance=int(season.coins_end or 0),
            bot_balance=int(season.bot_coins_end or session.result_coins_bot or 0),
        )
        db.refresh(session)
        next_season = None
    elif not next_season:
        session = _finalize_completed_session(db, session)
        db.refresh(session)
    try:
        season_meta = json.loads(season.meta_json or "{}")
    except Exception:
        season_meta = {}

    leaderboard = (
        _build_session_leaderboard(db, session)
        if _reason_completed_for_session(session) == "NORMAL_COMPLETION"
        else []
    )

    res = {
        "coinsStart": season.coins_start,
        "coinsEnd": season.coins_end,
        "profit": season.profit,
        "botCoinsEnd": season.bot_coins_end,
        "debtTotal": session.debt_total,
        "debtRate": session.debt_rate,
        "salesProfit": int(season_meta.get("tradeSellTotal", 0) or 0),
        "tradeBuyTotal": int(season_meta.get("tradeBuyTotal", 0) or 0),
        "tradeProfit": int(season_meta.get("tradeProfit", 0) or 0),
        "creditsTaken": int(season_meta.get("creditsTaken", 0) or 0),
        "creditsRepaid": int(season_meta.get("creditsRepaid", 0) or 0),
        "creditDelta": int(season_meta.get("creditsTaken", 0) or 0) - int(season_meta.get("creditsRepaid", 0) or 0),
        "interestPaid": int(season_meta.get("interestPaid", 0) or 0),
        "utilityPaid": int(season_meta.get("utilityPaid", 0) or 0),
        "escapedCats": int(nursery_transition.get("escapedCount", 0) or 0),
        "escapedCatIds": list(nursery_transition.get("escapedCatIds") or []),
        "escapedAnimals": list(nursery_transition.get("escapedAnimals") or []),
        "sessionStatus": _session_status_for_platform(session),
        "completionReason": _reason_completed_for_session(session),
        "terminal": _is_session_terminal(session),
        "completedAllSeasons": bool(int(session.season_count_completed or 0) >= int(crud.SEASONS_TOTAL)),
        "finalPlace": int(session.final_place or 0),
        "finalBalance": int(session.final_balance or session.result_coins_player or 0),
        "seasonCountCompleted": int(session.season_count_completed or 0),
        "leaderboard": leaderboard,
        "meta": season_meta,
    }
    nxt = None
    if next_season:
        nxt = {"number": next_season.season_number, "secondsLeft": crud.SEASON_SECONDS[next_season.season_number], "coins": next_season.coins_end}
    _mark_session_activity(db, session)
    return {"seasonResult": res, "nextSeason": nxt}


@app.post("/api/game/session/finish", response_model=SessionFinishOut)
def game_session_finish(payload: SessionFinishIn, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"status": "error", "playerCoins": 0, "botCoins": 0}
    _ensure_session_not_timed_out(db, session)

    session = _finalize_completed_session(db, session)
    return {"status": session.status, "playerCoins": session.result_coins_player, "botCoins": session.result_coins_bot}


@app.post("/api/analytics/compute/{session_id}", response_model=CompetencyProfileOut)
def analytics_compute(session_id: str, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"sessionId": session_id, "overall": 0, "competencies": [], "recommendations": []}
    
    competencies = crud.compute_competencies(db, session_id)

    overall = 0
    if competencies:
        overall = round(sum(c["score"] for c in competencies) / len(competencies))

    recommendations = _build_recommendations(competencies)

    return {
        "sessionId": session_id,
        "overall": overall,
        "competencies": competencies,
        "recommendations": recommendations,
    }



@app.get("/api/game/season/state", response_model=SeasonStateOut)
def season_state(
    sessionId: str = Query(...),
    seasonNumber: int = Query(...),
    counterpartyType: str | None = Query(default=None),
    counterpartyId: int | None = Query(default=None),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, sessionId)
    if not session or session.user_id != user.id:
        return {
            "sessionId": sessionId,
            "seasonNumber": seasonNumber,
            "role": "cattery",
            "adultAge": ADULT_AGE,
            "coins": 0,
            "debtTotal": 0,
            "debtRate": 0.0,
            "market": {},
            "inventory": {},
            "inventoryEntities": [],
        }
    _ensure_session_not_timed_out(db, session)

    season = (
        db.query(Season)
        .filter(
            Season.session_id == sessionId,
            Season.season_number == seasonNumber,
        )
        .order_by(Season.started_at.desc(), Season.id.desc())
        .first()
    )

    coins = season.coins_end if season else 0
    market = _market_view_for_session(
        db,
        session,
        seasonNumber,
        counterparty_type=counterpartyType,
        counterparty_id=counterpartyId,
    )
    inventory, inventory_entities = crud.get_inventory_view(session.inventory_json or "{}")


    return {
        "sessionId": sessionId,
        "seasonNumber": seasonNumber,
        "role": session.assigned_role,
        "adultAge": ADULT_AGE,
        "coins": coins,
        "debtTotal": session.debt_total,
        "debtRate": float(session.debt_rate),
        "market": market,
        "inventory": inventory,
        "inventoryEntities": inventory_entities,
    }


@app.get("/api/game/progress/{session_id}/{season_number}", response_model=GameProgressGetOut)
def game_progress_get(
    session_id: str,
    season_number: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"found": False, "progress": None}
    _ensure_session_not_timed_out(db, session)

    progress = crud.get_game_progress(db, session_id, season_number)
    if not progress:
        return {"found": False, "progress": None}

    try:
        nursery = json.loads(progress.nursery_json or "{}")
        if not isinstance(nursery, dict):
            nursery = {}
    except Exception:
        nursery = {}

    return {
        "found": True,
        "progress": {
            "sessionId": session_id,
            "seasonNumber": season_number,
            "nursery": nursery,
            "nurseryCoinsDelta": int(progress.nursery_coins_delta or 0),
            "timeLeft": int(progress.time_left or 0),
            "updatedAt": progress.updated_at.isoformat() if progress.updated_at else None,
        },
    }


@app.post("/api/game/progress/save", response_model=GameProgressOut)
def game_progress_save(
    payload: GameProgressSaveIn,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=400, detail="invalid_session")
    _ensure_session_not_timed_out(db, session)

    progress = crud.save_game_progress(
        db=db,
        session_id=payload.sessionId,
        season_number=payload.seasonNumber,
        nursery=payload.nursery if isinstance(payload.nursery, dict) else {},
        nursery_coins_delta=payload.nurseryCoinsDelta,
        time_left=payload.timeLeft,
    )
    try:
        nursery = json.loads(progress.nursery_json or "{}")
        if not isinstance(nursery, dict):
            nursery = {}
    except Exception:
        nursery = {}
    _mark_session_activity(db, session)

    return {
        "sessionId": payload.sessionId,
        "seasonNumber": payload.seasonNumber,
        "nursery": nursery,
        "nurseryCoinsDelta": int(progress.nursery_coins_delta or 0),
        "timeLeft": int(progress.time_left or 0),
        "updatedAt": progress.updated_at.isoformat() if progress.updated_at else None,
    }


@app.get("/api/game/cattery-public/{session_id}/{season_number}/{cattery_id}", response_model=CatteryPublicViewOut)
def game_cattery_public_view(
    session_id: str,
    season_number: int,
    cattery_id: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="invalid_session")
    _ensure_session_not_timed_out(db, session)

    ensure_competitors_for_session(db, session)
    data = get_public_spectate_view(
        db=db,
        session_id=session_id,
        season_number=season_number,
        cattery_id=cattery_id,
    )
    if not data:
        raise HTTPException(status_code=404, detail="cattery_not_found")
    db.commit()
    return data


@app.get("/api/game/sessions", response_model=list[GameSessionItemOut])
def game_sessions(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id)
        .order_by(GameSession.started_at.desc())
        .all()
    )
    now = _now_utc()
    for s in sessions:
        if _finalize_session_by_money_if_needed(db, s):
            db.refresh(s)
            continue
        if _finalize_session_by_completed_seasons_if_needed(db, s):
            db.refresh(s)
            continue
        if _is_session_active(s) and s.inactive_timeout_at and now > s.inactive_timeout_at:
            _finalize_session_by_inactivity(db, s)
            db.refresh(s)

    return [
        {
            "id": s.id,
            "assignedRole": s.assigned_role,
            "status": s.status,
            "startedAt": s.started_at.isoformat() if s.started_at else "",
            "finishedAt": s.finished_at.isoformat() if s.finished_at else None,
            "resultCoinsPlayer": s.result_coins_player,
            "resultCoinsBot": s.result_coins_bot,
        }
        for s in sessions
    ]


@app.get("/api/game/session/{session_id}", response_model=GameSessionDetailOut)
def game_session_detail(session_id: str, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        return {"session": None, "seasons": []}
    if _finalize_session_by_money_if_needed(db, session):
        db.refresh(session)
    if _finalize_session_by_completed_seasons_if_needed(db, session):
        db.refresh(session)
    if _is_session_active(session) and session.inactive_timeout_at and _now_utc() > session.inactive_timeout_at:
        _finalize_session_by_inactivity(db, session)
        db.refresh(session)

    seasons = (
        db.query(Season)
        .filter(Season.session_id == session_id)
        .order_by(Season.season_number.asc())
        .all()
    )
    return {
        "session": {
            "id": session.id,
            "assignedRole": session.assigned_role,
            "status": session.status,
            "startedAt": session.started_at.isoformat() if session.started_at else "",
            "finishedAt": session.finished_at.isoformat() if session.finished_at else None,
            "resultCoinsPlayer": session.result_coins_player,
            "resultCoinsBot": session.result_coins_bot,
        },
        "seasons": [
            {
                "season_number": s.season_number,
                "coins_start": s.coins_start,
                "coins_end": s.coins_end,
                "profit": s.profit,
                "bot_coins_end": s.bot_coins_end,
                "meta_json": s.meta_json or "{}",
            }
            for s in seasons
        ],
    }


def _get_latest_playable_session_for_user(db: Session, user_id: str) -> GameSession | None:
    sessions = (
        db.query(GameSession)
        .filter(GameSession.user_id == user_id, GameSession.status.in_(["active", "not_started"]))
        .order_by(GameSession.started_at.desc())
        .all()
    )
    now = _now_utc()
    for session in sessions:
        if _finalize_session_by_money_if_needed(db, session):
            continue
        if _finalize_session_by_completed_seasons_if_needed(db, session):
            continue
        if session.inactive_timeout_at and now > session.inactive_timeout_at:
            _finalize_session_by_inactivity(db, session)
            continue
        if _is_session_active(session):
            return session
    return None


@app.get("/api/sessions/active")
def sessions_active(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = _get_latest_playable_session_for_user(db, user.id)
    if not session:
        return {"hasActive": False, "session": None}

    current_season = (
        db.query(Season)
        .filter(Season.session_id == session.id)
        .order_by(Season.season_number.desc())
        .first()
    )
    return {
        "hasActive": True,
        "session": {
            "id": session.id,
            "status": _session_status_for_platform(session),
            "role": session.assigned_role,
            "seasonNumber": int(current_season.season_number) if current_season else 1,
            "startedAt": session.started_at.isoformat() if session.started_at else None,
            "lastActionAt": session.last_action_at.isoformat() if session.last_action_at else None,
            "inactiveTimeoutAt": session.inactive_timeout_at.isoformat() if session.inactive_timeout_at else None,
        },
    }


@app.post("/api/sessions/start")
def sessions_start(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    active = _get_latest_playable_session_for_user(db, user.id)
    if active:
        season = (
            db.query(Season)
            .filter(Season.session_id == active.id)
            .order_by(Season.season_number.desc())
            .first()
        )
        return {
            "ok": True,
            "created": False,
            "sessionId": active.id,
            "seasonNumber": int(season.season_number) if season else 1,
            "status": _session_status_for_platform(active),
        }
    # New session entry counts as activity by definition.

    session = crud.start_game_session(db, user.id)
    _mark_session_activity(db, session)
    return {
        "ok": True,
        "created": True,
        "sessionId": session.id,
        "seasonNumber": 1,
        "status": _session_status_for_platform(session),
    }


@app.post("/api/sessions/{session_id}/continue")
def sessions_continue(session_id: str, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Session not found"})
    if _finalize_session_by_money_if_needed(db, session):
        _raise_session_not_active(session)
    if _finalize_session_by_completed_seasons_if_needed(db, session):
        _raise_session_not_active(session)
    if _is_session_active(session) and session.inactive_timeout_at and _now_utc() > session.inactive_timeout_at:
        _finalize_session_by_inactivity(db, session)
        _raise_session_not_active(session)
    if session.status not in {"active", "not_started"}:
        _raise_session_not_active(session)
    season = (
        db.query(Season)
        .filter(Season.session_id == session.id)
        .order_by(Season.season_number.desc())
        .first()
    )
    season_number = int(season.season_number) if season else 1
    # Explicit session enter: whitelist action that resets inactivity timer.
    _mark_session_activity(db, session)
    return {
        "ok": True,
        "sessionId": session.id,
        "seasonNumber": season_number,
        "playUrl": f"/play/{session.id}/{season_number}",
    }


@app.get("/api/sessions/history")
def sessions_history(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id)
        .order_by(GameSession.started_at.desc())
        .all()
    )
    now = _now_utc()
    changed = False
    for session in sessions:
        if _finalize_session_by_money_if_needed(db, session):
            changed = True
            db.refresh(session)
            continue
        if _finalize_session_by_completed_seasons_if_needed(db, session):
            changed = True
            db.refresh(session)
            continue
        if _is_session_active(session) and session.inactive_timeout_at and now > session.inactive_timeout_at:
            _finalize_session_by_inactivity(db, session)
            changed = True
            db.refresh(session)

    delta_map = {
        row.session_id: row
        for row in (
            db.query(SessionCompetencyDelta)
            .filter(SessionCompetencyDelta.user_id == user.id)
            .all()
        )
    }
    result_map = {
        row.session_id: row
        for row in (
            db.query(GameSessionResult)
            .filter(GameSessionResult.user_id == user.id)
            .all()
        )
    }
    items = []
    for session in sessions:
        if session.status in {"completed", "bankrupt_completed", "finished"} and session.id not in delta_map:
            delta_map[session.id] = _sync_session_competencies(db, session)
            changed = True
        if session.status in {"completed", "bankrupt_completed", "finished"} and session.id not in result_map:
            result_map[session.id] = (
                db.query(GameSessionResult)
                .filter(GameSessionResult.session_id == session.id)
                .one_or_none()
            )
        delta = delta_map.get(session.id)
        result = result_map.get(session.id)
        items.append(
            {
                "id": session.id,
                "sessionType": "Стандарт",
                "simulation": "Business Cats",
                "ratingType": "Рейтингуемая",
                "participants": "1/1",
                "startedAt": session.started_at.isoformat() if session.started_at else None,
                "finishedAt": session.finished_at.isoformat() if session.finished_at else None,
                "role": "Питомник" if session.assigned_role == "cattery" else "Магазин",
                "status": _session_status_for_platform(session),
                "wasActiveAtView": _is_session_active(session),
                "finalPlace": int(session.final_place or (result.place if result else 0) or (delta.place_awarded if delta else 0) or 0),
                "finalBalance": int(session.final_balance or (result.final_balance if result else 0) or session.result_coins_player or 0),
                "reason": session.finish_reason,
                "reasonCompleted": _reason_completed_for_session(session, result),
                "bankruptReason": session.bankrupt_reason or (result.bankrupt_reason if result else "NONE"),
                "seasonCountCompleted": int(session.season_count_completed or 0),
                "totalDelta": round(float(result.total_delta), 2) if result else round(float((delta.analytics_delta + delta.negotiation_delta + delta.strategy_delta) if delta else 0.0), 2),
                "competencyDelta": {
                    "analytics": round(float(result.analytics_delta), 2) if result else (round(float(delta.analytics_delta), 2) if delta else 0.0),
                    "negotiation": round(float(result.negotiation_delta), 2) if result else (round(float(delta.negotiation_delta), 2) if delta else 0.0),
                    "strategy": round(float(result.strategy_delta), 2) if result else (round(float(delta.strategy_delta), 2) if delta else 0.0),
                },
            }
        )
    if changed:
        db.commit()
    return {"items": items}


@app.get("/api/sessions/{session_id}/details")
def sessions_details(session_id: str, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Session not found"})
    if _finalize_session_by_money_if_needed(db, session):
        db.refresh(session)
    if _finalize_session_by_completed_seasons_if_needed(db, session):
        db.refresh(session)
    if _is_session_active(session) and session.inactive_timeout_at and _now_utc() > session.inactive_timeout_at:
        _finalize_session_by_inactivity(db, session)
        db.refresh(session)

    if session.status in {"completed", "bankrupt_completed", "finished"}:
        delta = (
            db.query(SessionCompetencyDelta)
            .filter(SessionCompetencyDelta.session_id == session.id)
            .one_or_none()
        )
        result = (
            db.query(GameSessionResult)
            .filter(GameSessionResult.session_id == session.id)
            .one_or_none()
        )
        if not delta:
            delta = _sync_session_competencies(db, session)
            db.commit()
            result = (
                db.query(GameSessionResult)
                .filter(GameSessionResult.session_id == session.id)
                .one_or_none()
            )
    else:
        delta = (
            db.query(SessionCompetencyDelta)
            .filter(SessionCompetencyDelta.session_id == session.id)
            .one_or_none()
        )
        result = (
            db.query(GameSessionResult)
            .filter(GameSessionResult.session_id == session.id)
            .one_or_none()
        )

    seasons = (
        db.query(Season)
        .filter(Season.session_id == session.id)
        .order_by(Season.season_number.asc())
        .all()
    )
    return {
        "id": session.id,
        "status": _session_status_for_platform(session),
        "wasActiveAtView": _is_session_active(session),
        "finalPlace": int(session.final_place or (result.place if result else 0) or (delta.place_awarded if delta else 0) or 0),
        "finalBalance": int(session.final_balance or (result.final_balance if result else 0) or session.result_coins_player or 0),
        "reason": session.finish_reason,
        "reasonCompleted": _reason_completed_for_session(session, result),
        "bankruptReason": session.bankrupt_reason or (result.bankrupt_reason if result else "NONE"),
        "inactiveBankrupt": bool(session.inactive_bankrupt),
        "seasonCountCompleted": int(session.season_count_completed or 0),
        "totalDelta": round(float(result.total_delta), 2) if result else round(float((delta.analytics_delta + delta.negotiation_delta + delta.strategy_delta) if delta else 0.0), 2),
        "competencyDelta": {
            "analytics": round(float(result.analytics_delta), 2) if result else (round(float(delta.analytics_delta), 2) if delta else 0.0),
            "negotiation": round(float(result.negotiation_delta), 2) if result else (round(float(delta.negotiation_delta), 2) if delta else 0.0),
            "strategy": round(float(result.strategy_delta), 2) if result else (round(float(delta.strategy_delta), 2) if delta else 0.0),
        },
        "result": {
            "place": int(result.place) if result else int(session.final_place or 0),
            "finalBalance": int(result.final_balance) if result else int(session.final_balance or 0),
            "bankruptReason": result.bankrupt_reason if result else (session.bankrupt_reason or "NONE"),
            "totalDelta": round(float(result.total_delta), 2) if result else 0.0,
            "analyticsDelta": round(float(result.analytics_delta), 2) if result else 0.0,
            "negotiationDelta": round(float(result.negotiation_delta), 2) if result else 0.0,
            "strategyDelta": round(float(result.strategy_delta), 2) if result else 0.0,
            "endedAt": result.ended_at.isoformat() if result and result.ended_at else (session.finished_at.isoformat() if session.finished_at else None),
            "reason": result.reason if result else (session.finish_reason or "SEASONS_COMPLETED"),
        },
        "seasons": [
            {
                "seasonNumber": int(s.season_number),
                "coinsStart": int(s.coins_start or 0),
                "coinsEnd": int(s.coins_end or 0),
                "profit": int(s.profit or 0),
                "botCoinsEnd": int(s.bot_coins_end or 0),
                "endedAt": s.ended_at.isoformat() if s.ended_at else None,
            }
            for s in seasons
        ],
    }


def _build_recommendations(competencies: list[dict]) -> list[str]:
    recs: list[str] = []
    for c in competencies:
        name = c.get("name", "")
        score = int(c.get("score", 0))
        ev = c.get("evidence", {}) or {}

        if name.startswith("Profitability") and score < 40:
            avg_profit = ev.get("avgProfit")
            prof = ev.get("profitableSeasons")
            seasons = ev.get("seasons")
            recs.append(
                f"Улучшите маржу и частоту прибыльных сделок (avgProfit={avg_profit}, profitableSeasons={prof}/{seasons})."
            )
        elif name.startswith("Cost Control") and score < 40:
            utility = ev.get("utilityPaid")
            interest = ev.get("interestPaid")
            recs.append(
                f"Снизьте коммунальные и процентные издержки (utilityPaid={utility}, interestPaid={interest})."
            )
        elif name.startswith("Debt Management") and score < 40:
            taken = ev.get("creditsTaken")
            repaid = ev.get("creditsRepaid")
            debt_end = ev.get("debtEnd")
            recs.append(
                f"Погашайте долг быстрее и не выходите на лимит (creditsTaken={taken}, creditsRepaid={repaid}, debtEnd={debt_end})."
            )
        elif name.startswith("Discipline") and score < 40:
            finish_early = ev.get("finishEarlySeasons")
            seasons = ev.get("seasons")
            recs.append(
                f"Не завершайте сезоны досрочно (finishEarlySeasons={finish_early}/{seasons})."
            )
    return recs


def _collect_target_user_ids(from_player_id: str, to_player_id: str) -> set[str]:
    targets: set[str] = set()
    for player_id in (from_player_id, to_player_id):
        if isinstance(player_id, str) and player_id.startswith("user:"):
            targets.add(player_id.split(":", 1)[1])
    return targets


def _trade_request_payload_for_user(req: TradeRequest, user_id: str | None) -> dict | None:
    if not user_id:
        return None
    viewer_player_id = trade_requests_service.user_player_id(user_id)
    return trade_requests_service._to_out(
        req,
        viewer_player_id=viewer_player_id,
        viewer_user_id=user_id,
    )


async def _schedule_bot_trade_response(session_id: str, request_id: str) -> None:
    await asyncio.sleep(trade_requests_service.bot_response_delay_seconds_for_request(request_id))
    db = SessionLocal()
    try:
        session = db.get(GameSession, session_id)
        if not session:
            return
        req = trade_requests_service.get_trade_request(db, session_id, request_id)
        if not req or not trade_requests_service.request_expects_bot_response(req):
            return

        previous_state = req.state
        updated = trade_requests_service.process_bot_response(db, session, req)
        if not updated:
            return
        db.commit()
        db.refresh(updated)

        request_for_viewer = _trade_request_payload_for_user(updated, session.user_id)
        if not request_for_viewer:
            return
        targets = _collect_target_user_ids(updated.from_player_id, updated.to_player_id)
        event_type = "trade.request.updated"
        if updated.state in {"ACCEPTED", "REJECTED", "CANCELLED", "EXPIRED"}:
            event_type = "trade.request.resolved"

        await trade_realtime_hub.publish(
            session_id=session_id,
            event_type=event_type,
            payload={
                "requestId": updated.id,
                "seasonId": updated.season_number,
                "state": updated.state,
                "status": request_for_viewer.get("status"),
                "previousState": previous_state,
                "messageCode": updated.message_code,
                "request": request_for_viewer,
            },
            target_user_ids=targets,
        )
    except Exception:
        db.rollback()
    finally:
        db.close()


@app.get("/api/game/trade-requests/{session_id}/{season_number}", response_model=TradeRequestListOut)
async def trade_requests_list(
    session_id: str,
    season_number: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="invalid_session")

    viewer_player_id = trade_requests_service.user_player_id(user.id)

    items = trade_requests_service.list_trade_requests(
        db=db,
        session_id=session_id,
        season_number=season_number,
        viewer_player_id=viewer_player_id,
        viewer_user_id=user.id,
    )
    db.commit()
    return {"items": items}


@app.post("/api/game/trade-requests/send", response_model=TradeRequestActionOut)
async def trade_requests_send(
    payload: TradeRequestSendIn,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "request": None}
    _ensure_session_not_timed_out(db, session)

    if session.assigned_role == "cattery" and payload.counterpartyType != "shop":
        return {"ok": False, "error": "invalid_counterparty_for_role", "request": None}

    from_player_id = trade_requests_service.user_player_id(user.id)
    to_player_id = trade_requests_service.counterparty_player_id(payload.counterpartyType, payload.counterpartyId)
    try:
        req = trade_requests_service.create_trade_request(
            db=db,
            session=session,
            season_number=payload.seasonNumber,
            from_player_id=from_player_id,
            to_player_id=to_player_id,
            items=[item.model_dump() for item in payload.items],
            ttl_seconds=payload.ttlSeconds,
        )
        db.commit()
        db.refresh(req)
    except ValueError as exc:
        db.rollback()
        return {"ok": False, "error": str(exc), "request": None}

    request_for_viewer = _trade_request_payload_for_user(req, user.id)
    targets = _collect_target_user_ids(req.from_player_id, req.to_player_id)
    await trade_realtime_hub.publish(
        session_id=payload.sessionId,
        event_type="trade.request.created",
        payload={
            "requestId": req.id,
            "seasonId": req.season_number,
            "state": req.state,
            "status": request_for_viewer.get("status") if request_for_viewer else None,
            "messageCode": req.message_code,
            "request": request_for_viewer,
        },
        target_user_ids=targets,
    )
    if req.state in {"ACCEPTED", "REJECTED", "CANCELLED", "EXPIRED"}:
        await trade_realtime_hub.publish(
            session_id=payload.sessionId,
            event_type="trade.request.resolved",
            payload={
                "requestId": req.id,
                "seasonId": req.season_number,
                "state": req.state,
                "status": request_for_viewer.get("status") if request_for_viewer else None,
                "messageCode": req.message_code,
                "request": request_for_viewer,
            },
            target_user_ids=targets,
        )
    elif req.state != "PENDING":
        await trade_realtime_hub.publish(
            session_id=payload.sessionId,
            event_type="trade.request.updated",
            payload={
                "requestId": req.id,
                "seasonId": req.season_number,
                "state": req.state,
                "status": request_for_viewer.get("status") if request_for_viewer else None,
                "messageCode": req.message_code,
                "request": request_for_viewer,
            },
            target_user_ids=targets,
        )

    if trade_requests_service.request_expects_bot_response(req):
        asyncio.create_task(_schedule_bot_trade_response(payload.sessionId, req.id))

    _mark_session_activity(db, session)
    return {"ok": True, "error": None, "request": request_for_viewer}


@app.post("/api/game/trade-requests/{request_id}/action", response_model=TradeRequestActionOut)
async def trade_requests_action(
    request_id: str,
    payload: TradeRequestActionIn,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, payload.sessionId)
    if not session or session.user_id != user.id:
        return {"ok": False, "error": "invalid_session", "request": None}
    _ensure_session_not_timed_out(db, session)

    req = trade_requests_service.get_trade_request(db, payload.sessionId, request_id)
    if not req:
        return {"ok": False, "error": "not_found", "request": None}
    if req.season_number != payload.seasonNumber:
        return {"ok": False, "error": "invalid_season", "request": None}

    actor_player_id = trade_requests_service.user_player_id(user.id)
    previous_state = req.state
    try:
        req = trade_requests_service.apply_trade_action(
            db=db,
            session=session,
            request_obj=req,
            actor_player_id=actor_player_id,
            action=payload.action,
            counter_items=[item.model_dump() for item in payload.counterItems],
            message_code=payload.messageCode,
        )
        db.commit()
        db.refresh(req)
    except ValueError as exc:
        db.rollback()
        return {"ok": False, "error": str(exc), "request": None}

    request_for_viewer = _trade_request_payload_for_user(req, user.id)
    targets = _collect_target_user_ids(req.from_player_id, req.to_player_id)

    if payload.action == "ack":
        hidden_for_actor = req.hidden_by_from if req.from_player_id == actor_player_id else req.hidden_by_to
        if hidden_for_actor:
            await trade_realtime_hub.publish(
                session_id=payload.sessionId,
                event_type="trade.request.deletedFromInbox",
                payload={
                    "requestId": req.id,
                    "seasonId": req.season_number,
                    "state": req.state,
                    "status": request_for_viewer.get("status") if request_for_viewer else None,
                },
                target_user_ids={user.id},
            )
        _mark_session_activity(db, session)
        return {"ok": True, "error": None, "request": request_for_viewer}

    event_type = "trade.request.updated"
    if req.state in {"ACCEPTED", "REJECTED", "CANCELLED", "EXPIRED"}:
        event_type = "trade.request.resolved"
    elif previous_state != req.state:
        event_type = "trade.request.updated"

    await trade_realtime_hub.publish(
        session_id=payload.sessionId,
        event_type=event_type,
        payload={
            "requestId": req.id,
            "seasonId": req.season_number,
            "state": req.state,
            "previousState": previous_state,
            "status": request_for_viewer.get("status") if request_for_viewer else None,
            "messageCode": req.message_code,
            "request": request_for_viewer,
        },
        target_user_ids=targets,
    )
    if trade_requests_service.request_expects_bot_response(req):
        asyncio.create_task(_schedule_bot_trade_response(payload.sessionId, req.id))
    _mark_session_activity(db, session)
    return {"ok": True, "error": None, "request": request_for_viewer}


@app.websocket("/api/game/trade-requests/ws/{session_id}")
async def trade_requests_ws(websocket: WebSocket, session_id: str):
    db = SessionLocal()
    try:
        user = get_ws_current_user(websocket, db)
        if not user or user.status != "ACTIVE":
            await websocket.close(code=1008, reason="Unauthorized")
            return
        session = db.get(GameSession, session_id)
        if not session or session.user_id != user.id:
            await websocket.close(code=1008, reason="Invalid session")
            return
    finally:
        db.close()

    await trade_realtime_hub.connect(session_id=session_id, user_id=user.id, websocket=websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_text(json.dumps({"eventType": "pong"}))
    except WebSocketDisconnect:
        await trade_realtime_hub.disconnect(session_id=session_id, websocket=websocket)
    except Exception:
        await trade_realtime_hub.disconnect(session_id=session_id, websocket=websocket)


@app.get("/api/analytics/profile", response_model=CompetencyProfileOut)
def analytics_profile(user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    session = (
        db.query(GameSession)
        .filter(GameSession.user_id == user.id, GameSession.status == "finished")
        .order_by(GameSession.finished_at.desc())
        .first()
    )
    if not session:
        return {"sessionId": "", "overall": 0, "competencies": [], "recommendations": []}

    competencies = crud.compute_competencies(db, session.id)
    overall = 0
    if competencies:
        overall = round(sum(c["score"] for c in competencies) / len(competencies))

    recommendations = _build_recommendations(competencies)
    return {
        "sessionId": session.id,
        "overall": overall,
        "competencies": competencies,
        "recommendations": recommendations,
    }


@app.get("/api/analytics/report/{session_id}")
def analytics_report(session_id: str, user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    if user.role != "candidate":
        raise HTTPException(status_code=403, detail="Only candidate can access report")

    session = db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    seasons = (
        db.query(Season)
        .filter(Season.session_id == session_id)
        .order_by(Season.season_number.asc())
        .all()
    )
    competencies = crud.compute_competencies(db, session_id)
    recommendations = _build_recommendations(competencies)

    pdf_bytes = generate_competency_report(
        candidate_profile=profile,
        session=session,
        seasons=seasons,
        competencies=competencies,
        recommendations=recommendations,
    )
    filename = f"business_cats_report_{session_id}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
