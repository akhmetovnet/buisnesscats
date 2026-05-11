from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    DATABASE_URL: str = 'sqlite:///./business_cats.db'

    JWT_ACCESS_SECRET: str = 'dev-access-secret-change-me'
    JWT_REFRESH_SECRET: str = 'dev-refresh-secret-change-me'

    ACCESS_TTL_MINUTES: int = 15
    REFRESH_TTL_HOURS: int = 12
    REFRESH_TTL_DAYS_REMEMBER: int = 30

    COOKIE_ACCESS_NAME: str = 'bc_access_token'
    COOKIE_REFRESH_NAME: str = 'bc_refresh_token'
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str | None = None
    COOKIE_SAMESITE: str = 'lax'

    APP_BASE_URL: str = 'http://localhost:5173'

    EMAIL_PROVIDER: str = 'console'
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    SMTP_FROM: str = 'Cattary Manager <noreply@businesscats.local>'

    AUTH_LOCKOUT_MINUTES: int = 10

    CORS_ALLOW_ORIGINS: str = 'http://localhost:3000,http://localhost:5173,http://localhost:8081'

    NODE_ENV: str = Field(default='development')

    @property
    def is_production(self) -> bool:
        return self.NODE_ENV.lower() == 'production'

    @field_validator('COOKIE_DOMAIN', mode='before')
    @classmethod
    def normalize_cookie_domain(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @property
    def dev_email_preview_enabled(self) -> bool:
        return not self.is_production

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(',') if origin.strip()]


settings = AppSettings()
