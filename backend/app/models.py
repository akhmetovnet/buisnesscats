import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, UniqueConstraint, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .game_config import CONFIG_START_COINS

def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # candidate|hr|admin
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_role: Mapped[str] = mapped_column(String(20), default="USER")
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    education_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    education_place: Mapped[str | None] = mapped_column(String(240), nullable=True)
    directions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    university: Mapped[str | None] = mapped_column(String(240), nullable=True)
    event_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    desired_specialties: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile", back_populates="user", uselist=False
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True)

    full_name: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    university: Mapped[str] = mapped_column(String(200), default="")
    program: Mapped[str] = mapped_column(String(200), default="")
    study_year: Mapped[int] = mapped_column(Integer, default=0)
    skills_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON строка

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="profile")

class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    assigned_role: Mapped[str] = mapped_column(String(20), nullable=False)  # cattery|petshop
    game_version: Mapped[str] = mapped_column(String(50), default="1.0-lite")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|finished|abandoned
    simulation_code: Mapped[str] = mapped_column(String(80), default="BUSINESS_CATS")
    session_type: Mapped[str] = mapped_column(String(40), default="STANDARD_SINGLE")
    rating_type: Mapped[str] = mapped_column(String(40), default="RATED")
    final_place: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_balance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inactive_bankrupt: Mapped[bool] = mapped_column(Boolean, default=False)
    inactive_timeout_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inactive_timeout_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    season_count_completed: Mapped[int] = mapped_column(Integer, default=0)
    finish_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bankrupt_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    result_coins_player: Mapped[int] = mapped_column(Integer, default=CONFIG_START_COINS)
    result_coins_bot: Mapped[int] = mapped_column(Integer, default=CONFIG_START_COINS)

    debt_total: Mapped[int] = mapped_column(Integer, default=0)         # текущий долг
    debt_rate: Mapped[float] = mapped_column(Float, default=0.0)        # средняя ставка (0.05 / 0.10 / 0.15)

    inventory_json: Mapped[str] = mapped_column(String, default='{"black":0,"white":0,"ginger":0,"gray":0}')


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..13
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    coins_start: Mapped[int] = mapped_column(Integer, default=CONFIG_START_COINS)
    coins_end: Mapped[int] = mapped_column(Integer, default=CONFIG_START_COINS)
    profit: Mapped[int] = mapped_column(Integer, default=0)
    bot_coins_end: Mapped[int] = mapped_column(Integer, default=CONFIG_START_COINS)
    
    from sqlalchemy import Text  # если нет
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")



class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")  # flexible gameplay payload, including nursery disease events
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompetencyResult(Base):
    __tablename__ = "competency_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)

    competency_code: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..100
    explain_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GameProgress(Base):
    __tablename__ = "game_progress"
    __table_args__ = (UniqueConstraint("session_id", "season_number", name="uq_progress_session_season"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)

    nursery_json: Mapped[str] = mapped_column(Text, default="{}")  # nursery state snapshot, including kitten disease fields
    nursery_coins_delta: Mapped[int] = mapped_column(Integer, default=0)
    time_left: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeRequest(Base):
    __tablename__ = "trade_requests"
    __table_args__ = (
        UniqueConstraint("session_id", "id", name="uq_trade_request_session_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)

    from_player_id: Mapped[str] = mapped_column(String(80), nullable=False)
    to_player_id: Mapped[str] = mapped_column(String(80), nullable=False)
    next_actor_player_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    state: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    request_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    total_price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    clarification_reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    clarification_meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    read_by_from: Mapped[bool] = mapped_column(Boolean, default=True)
    read_by_to: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_by_from: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_by_to: Mapped[bool] = mapped_column(Boolean, default=False)

    counter_of_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    parent_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    clarification_requested_by: Mapped[str | None] = mapped_column(String(80), nullable=True)

    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeRelation(Base):
    __tablename__ = "trade_relations"
    __table_args__ = (
        UniqueConstraint("session_id", "player_id", "counterparty_id", name="uq_trade_relation_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)
    player_id: Mapped[str] = mapped_column(String(80), nullable=False)
    counterparty_id: Mapped[str] = mapped_column(String(80), nullable=False)

    relation_score: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sent_requests_in_season: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_count_in_season: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TradeBotState(Base):
    __tablename__ = "trade_bot_states"
    __table_args__ = (
        UniqueConstraint("session_id", "bot_player_id", name="uq_trade_bot_state_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)
    bot_player_id: Mapped[str] = mapped_column(String(80), nullable=False)

    coins: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    inventory_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CatteryCompetitor(Base):
    __tablename__ = "cattery_competitors"
    __table_args__ = (
        UniqueConstraint("session_id", "cattery_id", name="uq_cattery_competitor_session_slot"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)
    cattery_id: Mapped[int] = mapped_column(Integer, nullable=False)

    is_player: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    archetype: Mapped[str] = mapped_column(String(40), nullable=False, default="BALANCER")

    coins: Mapped[int] = mapped_column(Integer, nullable=False, default=CONFIG_START_COINS)
    houses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reserve_coins_target: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # Private bot data (not exposed in SPECTATE endpoint)
    state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Public showcase data (safe to expose in SPECTATE)
    public_catalog_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    season_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    deals_this_season: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_sell_price_this_season: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_deal_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    replaced_by_token_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("refresh_tokens.id"), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remember_me: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    result_code: Mapped[str] = mapped_column(String(80), nullable=False, default="OK")


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (
        UniqueConstraint("action", "key", name="uq_auth_rate_limit_action_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompetencyProgress(Base):
    __tablename__ = "competency_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_competency_progress_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    analytics_level: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    negotiation_level: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    strategy_level: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    analytics_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    negotiation_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    strategy_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_analytics_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_negotiation_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_strategy_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SessionCompetencyDelta(Base):
    __tablename__ = "session_competency_delta"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_session_competency_delta_session"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False, index=True)
    analytics_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negotiation_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    strategy_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    place_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GameSessionResult(Base):
    __tablename__ = "game_session_results"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_game_session_result_session"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False, index=True)
    place: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    final_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bankrupt_reason: Mapped[str] = mapped_column(String(40), nullable=False, default="NONE")
    total_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    analytics_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    negotiation_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    strategy_delta: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ended_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reason: Mapped[str] = mapped_column(String(80), nullable=False, default="SEASONS_COMPLETED")
    stats_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
