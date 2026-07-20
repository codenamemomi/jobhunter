FROM python:3.11-slim

WORKDIR /app

# System deps often needed for weasyprint/psycopg on slim images
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT; default 8000 for local Docker
ENV PORT=8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
