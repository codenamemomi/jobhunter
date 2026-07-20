"""SQLAlchemy engine and session configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

connect_args = {}
if settings.is_sqlite:
    # Required for SQLite + FastAPI multi-thread request handling
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
    """FastAPI dependency that yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lightweight column adds for existing SQLite DBs (create_all won't alter tables)
_CV_EXTRA_COLUMNS: dict[str, str] = {
    "original_filename": "VARCHAR(512)",
    "file_path": "VARCHAR(1024)",
    "raw_text": "TEXT",
    "parsed_skills": "TEXT",
    "parsed_titles": "TEXT",
    "parsed_keywords": "TEXT",
    "parsed_at": "DATETIME",
}


def _migrate_sqlite_columns() -> None:
    if not settings.is_sqlite:
        return
    insp = inspect(engine)
    if "cvs" not in insp.get_table_names():
        return
    existing = {col["name"] for col in insp.get_columns("cvs")}
    with engine.begin() as conn:
        for name, col_type in _CV_EXTRA_COLUMNS.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE cvs ADD COLUMN {name} {col_type}"))


def init_db() -> None:
    """Create all tables. Import models so metadata is registered."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
