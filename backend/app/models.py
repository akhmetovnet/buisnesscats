import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from sqlalchemy import Float

def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # candidate|hr|admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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

from sqlalchemy import Boolean

class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    assigned_role: Mapped[str] = mapped_column(String(20), nullable=False)  # cattery|petshop
    game_version: Mapped[str] = mapped_column(String(50), default="1.0-lite")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|finished|abandoned

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    result_coins_player: Mapped[int] = mapped_column(Integer, default=40)
    result_coins_bot: Mapped[int] = mapped_column(Integer, default=40)

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

    coins_start: Mapped[int] = mapped_column(Integer, default=40)
    coins_end: Mapped[int] = mapped_column(Integer, default=40)
    profit: Mapped[int] = mapped_column(Integer, default=0)
    bot_coins_end: Mapped[int] = mapped_column(Integer, default=40)
    
    from sqlalchemy import Text  # если нет
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")



class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)

    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompetencyResult(Base):
    __tablename__ = "competency_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("game_sessions.id"), nullable=False)

    competency_code: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..100
    explain_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
