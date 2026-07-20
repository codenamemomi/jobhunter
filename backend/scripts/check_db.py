#!/usr/bin/env python3
"""Print DB connectivity and table list for the current DATABASE_URL."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine


def main() -> int:
    url = settings.sqlalchemy_database_url
    # redact password
    safe = url
    if "@" in url and "://" in url:
        head, rest = url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            userinfo, hostpart = rest.split("@", 1)
            user = userinfo.split(":", 1)[0]
            safe = f"{head}://{user}:***@{hostpart}"

    print("dialect :", "sqlite" if settings.is_sqlite else "postgres" if settings.is_postgres else "other")
    print("url     :", safe)
    try:
        with engine.connect() as conn:
            if settings.is_postgres:
                ver = conn.execute(text("SELECT version()")).scalar()
                print("server  :", (ver or "")[:80])
            else:
                print("server  : sqlite")
            insp = inspect(engine)
            tables = sorted(insp.get_table_names())
            print("tables  :", tables or "(none)")
            if "alembic_version" in tables:
                rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                print("alembic :", rev)
            else:
                print("alembic : (no alembic_version table — run: alembic upgrade head)")
        print("OK")
        return 0
    except Exception as exc:  # noqa: BLE001
        print("ERROR  :", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
