#!/usr/bin/env bash
# Apply Alembic migrations against DATABASE_URL from backend/.env
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source venv/bin/activate
echo "DATABASE_URL dialect: $(python -c 'from app.config import settings; print(settings.sqlalchemy_database_url.split(\"://\")[0])')"
alembic upgrade head
echo "Migrations applied (alembic upgrade head)."
alembic current
