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

    # Database — SQLite locally; set to Supabase Postgres for live testing:
    # postgresql://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
    # or direct: postgresql://postgres:[PASSWORD]@db.[project].supabase.co:5432/postgres?sslmode=require
    database_url: str = "sqlite:///./jobhunter.db"

    # Auth / JWT
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # CORS — comma-separated exact origins (no trailing slash)
    # Must include your Vercel URL in production, e.g.
    # CORS_ORIGINS=http://localhost:5173,https://jobhunter-seven-mu.vercel.app
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,"
        "https://jobhunter-seven-mu.vercel.app"
    )
    # Also allow any *.vercel.app preview deploy (regex)
    cors_origin_regex: str = r"https://.*\.vercel\.app"

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

    # Auto-scrape (in-process scheduler + Celery schedule)
    auto_scrape_enabled: bool = True
    auto_scrape_interval_hours: float = 6.0
    auto_scrape_on_startup: bool = False  # set true to scrape when API boots
    auto_scrape_limit_per_source: int = 40
    auto_scrape_query: str = ""  # optional keyword for all sources
    # Comma-separated; empty = all free sources (+ Adzuna if keyed)
    auto_scrape_sources: str = ""

    @property
    def auto_scrape_sources_list(self) -> list[str]:
        if not self.auto_scrape_sources.strip():
            return []
        return [s.strip() for s in self.auto_scrape_sources.split(",") if s.strip()]

    @field_validator("brevo_api_key", "smtp_password", "smtp_user", "email_from", mode="before")
    @classmethod
    def _strip_secrets(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().strip('"').strip("'")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize URI for SQLAlchemy (postgres:// → postgresql://)."""
        url = (self.database_url or "").strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        u = self.sqlalchemy_database_url
        return u.startswith("postgresql://") or u.startswith("postgresql+")

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
