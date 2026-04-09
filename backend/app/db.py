from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .settings import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # важно для SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_auth_columns() -> None:
    """Backward-compatible schema patching for existing SQLite DB without alembic."""
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "users" not in tables:
            return

        existing_cols = {col["name"] for col in inspector.get_columns("users")}
        add_column_sql = {
            "email": "ALTER TABLE users ADD COLUMN email VARCHAR(254)",
            "password_hash": "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
            "status": "ALTER TABLE users ADD COLUMN status VARCHAR(40) DEFAULT 'ACTIVE'",
            "locked_until": "ALTER TABLE users ADD COLUMN locked_until DATETIME",
            "updated_at": "ALTER TABLE users ADD COLUMN updated_at DATETIME",
            "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME",
            "display_name": "ALTER TABLE users ADD COLUMN display_name VARCHAR(200)",
            "account_role": "ALTER TABLE users ADD COLUMN account_role VARCHAR(20) DEFAULT 'USER'",
        }
        for col_name, sql in add_column_sql.items():
            if col_name not in existing_cols:
                conn.execute(text(sql))

        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON users(email)"))


def ensure_platform_columns() -> None:
    """Backward-compatible schema patching for platform profile/session extensions."""
    with engine.begin() as conn:
        inspector = inspect(conn)
        tables = set(inspector.get_table_names())
        if "users" in tables:
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            user_add_sql = {
                "first_name": "ALTER TABLE users ADD COLUMN first_name VARCHAR(120)",
                "last_name": "ALTER TABLE users ADD COLUMN last_name VARCHAR(120)",
                "middle_name": "ALTER TABLE users ADD COLUMN middle_name VARCHAR(120)",
                "birth_date": "ALTER TABLE users ADD COLUMN birth_date DATETIME",
                "birth_place": "ALTER TABLE users ADD COLUMN birth_place VARCHAR(200)",
                "city": "ALTER TABLE users ADD COLUMN city VARCHAR(120)",
                "education_type": "ALTER TABLE users ADD COLUMN education_type VARCHAR(80)",
                "education_place": "ALTER TABLE users ADD COLUMN education_place VARCHAR(240)",
                "directions_json": "ALTER TABLE users ADD COLUMN directions_json TEXT DEFAULT '[]'",
                "university": "ALTER TABLE users ADD COLUMN university VARCHAR(240)",
                "event_code": "ALTER TABLE users ADD COLUMN event_code VARCHAR(120)",
                "desired_specialties": "ALTER TABLE users ADD COLUMN desired_specialties TEXT",
                "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(512)",
            }
            for col_name, sql in user_add_sql.items():
                if col_name not in user_cols:
                    conn.execute(text(sql))

        if "game_sessions" in tables:
            session_cols = {col["name"] for col in inspector.get_columns("game_sessions")}
            session_add_sql = {
                "simulation_code": "ALTER TABLE game_sessions ADD COLUMN simulation_code VARCHAR(80) DEFAULT 'BUSINESS_CATS'",
                "session_type": "ALTER TABLE game_sessions ADD COLUMN session_type VARCHAR(40) DEFAULT 'STANDARD_SINGLE'",
                "rating_type": "ALTER TABLE game_sessions ADD COLUMN rating_type VARCHAR(40) DEFAULT 'RATED'",
                "final_place": "ALTER TABLE game_sessions ADD COLUMN final_place INTEGER",
                "final_balance": "ALTER TABLE game_sessions ADD COLUMN final_balance INTEGER",
                "inactive_bankrupt": "ALTER TABLE game_sessions ADD COLUMN inactive_bankrupt BOOLEAN DEFAULT 0",
                "inactive_timeout_triggered": "ALTER TABLE game_sessions ADD COLUMN inactive_timeout_triggered BOOLEAN DEFAULT 0",
                "last_action_at": "ALTER TABLE game_sessions ADD COLUMN last_action_at DATETIME",
                "inactive_timeout_at": "ALTER TABLE game_sessions ADD COLUMN inactive_timeout_at DATETIME",
                "season_count_completed": "ALTER TABLE game_sessions ADD COLUMN season_count_completed INTEGER DEFAULT 0",
                "finish_reason": "ALTER TABLE game_sessions ADD COLUMN finish_reason VARCHAR(80)",
                "bankrupt_reason": "ALTER TABLE game_sessions ADD COLUMN bankrupt_reason VARCHAR(40)",
            }
            for col_name, sql in session_add_sql.items():
                if col_name not in session_cols:
                    conn.execute(text(sql))

        if "trade_requests" in tables:
            trade_request_cols = {col["name"] for col in inspector.get_columns("trade_requests")}
            trade_request_add_sql = {
                "thread_id": "ALTER TABLE trade_requests ADD COLUMN thread_id VARCHAR(36)",
                "request_type": "ALTER TABLE trade_requests ADD COLUMN request_type VARCHAR(32)",
                "direction": "ALTER TABLE trade_requests ADD COLUMN direction VARCHAR(32)",
                "clarification_reason": "ALTER TABLE trade_requests ADD COLUMN clarification_reason VARCHAR(40)",
                "clarification_meta_json": "ALTER TABLE trade_requests ADD COLUMN clarification_meta_json TEXT",
            }
            for col_name, sql in trade_request_add_sql.items():
                if col_name not in trade_request_cols:
                    conn.execute(text(sql))
