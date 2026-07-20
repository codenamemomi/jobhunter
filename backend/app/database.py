"""SQLAlchemy engine and session configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {}
if settings.is_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# table_name -> {column: sql_type}
_EXTRA_COLUMNS: dict[str, dict[str, str]] = {
    "cvs": {
        "original_filename": "VARCHAR(512)",
        "file_path": "VARCHAR(1024)",
        "raw_text": "TEXT",
        "parsed_skills": "TEXT",
        "parsed_titles": "TEXT",
        "parsed_keywords": "TEXT",
        "parsed_at": "DATETIME",
    },
    "jobs": {
        "apply_method": "VARCHAR(32) DEFAULT 'unknown'",
        "apply_email": "VARCHAR(255)",
        "apply_url": "VARCHAR(1024)",
    },
    "users": {
        "auto_draft_enabled": "BOOLEAN DEFAULT 0",
        "auto_send_enabled": "BOOLEAN DEFAULT 0",
        "auto_min_score": "FLOAT DEFAULT 75.0",
        "auto_daily_limit": "INTEGER DEFAULT 5",
        "auto_prefer_remote": "BOOLEAN DEFAULT 1",
        "auto_email_only": "BOOLEAN DEFAULT 1",
    },
    "applications": {
        "apply_channel": "VARCHAR(32)",
        "email_to": "VARCHAR(255)",
        "email_subject": "VARCHAR(512)",
        "email_body": "TEXT",
        "match_score": "FLOAT",
        "sent_at": "DATETIME",
        "send_error": "TEXT",
        "is_auto": "BOOLEAN DEFAULT 0",
    },
}


def _migrate_sqlite_columns() -> None:
    if not settings.is_sqlite:
        return
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table, cols in _EXTRA_COLUMNS.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, col_type in cols.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}"))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
