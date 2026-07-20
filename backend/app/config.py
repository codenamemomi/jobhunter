"""Application settings from environment variables."""

from functools import lru_cache
from typing import List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from env / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "JobHunter API"
    debug: bool = True
    api_prefix: str = "/api"

    # Database — SQLite by default so local dev works without Postgres
    database_url: str = "sqlite:///./jobhunter.db"

    # Auth / JWT
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # CORS (frontend Vite default + common local ports)
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # External job APIs (optional — free sources work without keys)
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "gb"

    # Email provider: auto | smtp | brevo | dry_run
    # auto = SMTP if smtp_password set, else Brevo if key set, else dry_run
    email_provider: str = "auto"

    # Shared from/reply identity
    email_from: str = "alerts@jobhunter.local"
    email_from_name: str = "JobHunter"

    # Brevo (Sendinblue) — EMAIL_FROM must be a verified sender in Brevo
    brevo_api_key: str = ""

    # SMTP / Gmail App Password
    # For Gmail: enable 2FA → create App Password → use below
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""  # usually same as EMAIL_FROM for Gmail
    smtp_password: str = ""  # Gmail app password (16 chars, spaces ok)
    smtp_use_tls: bool = True

    # Uploaded CVs
    upload_dir: str = "./uploads"

    @field_validator("brevo_api_key", "smtp_password", "smtp_user", "email_from", mode="before")
    @classmethod
    def _strip_secrets(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def resolved_email_provider(self) -> Literal["smtp", "brevo", "dry_run"]:
        mode = (self.email_provider or "auto").strip().lower()
        smtp_ready = bool(self.smtp_password and (self.smtp_user or self.email_from))
        brevo_ready = bool(self.brevo_api_key)

        if mode == "dry_run":
            return "dry_run"
        if mode == "smtp":
            if smtp_ready:
                return "smtp"
            # Incomplete Gmail config — fall back so apps still deliver
            if brevo_ready:
                return "brevo"
            return "dry_run"
        if mode == "brevo":
            if brevo_ready:
                return "brevo"
            if smtp_ready:
                return "smtp"
            return "dry_run"
        # auto: prefer Gmail app password when set, else Brevo
        if smtp_ready:
            return "smtp"
        if brevo_ready:
            return "brevo"
        return "dry_run"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear cache and reload .env (after editing secrets without full process restart)."""
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings


settings = get_settings()
