# JobHunter

Personal job-hunting platform: aggregate listings from multiple boards, match them to your CV, track applications, and apply by email when a listing exposes a contact address.

| Frontend | Backend (example) |
|----------|-------------------|
| [jobhunter-seven-mu.vercel.app](https://jobhunter-seven-mu.vercel.app) | Deployed separately (e.g. Render) |

---

## Features

- **Multi-source job scrape** — RemoteOK, Remotive, ArbeitNow, Jobicy, Himalayas, The Muse, optional Adzuna  
- **Search & filters** — keywords, location, company, remote, source, email-apply only  
- **CV upload & parse** — PDF/DOCX/TXT; rule-based skills/titles (no AI required)  
- **CV ↔ job matching** — score and rank roles against your profile  
- **Email apply** — draft + send application with your **uploaded** CV attachment  
- **Apply queue & tracker** — wishlist → draft → applied → interview pipeline  
- **Optional auto-apply** — draft (and optionally send) high-scoring email-apply jobs with daily limits  
- **Auto-scrape** — background scrape on an interval (in-process or Celery)  
- **Auth** — register / login / JWT  

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, Vite, React Router |
| Backend | FastAPI, SQLAlchemy, Pydantic Settings |
| DB | SQLite (local) or PostgreSQL / Supabase (live) |
| Migrations | Alembic |
| Email | Gmail SMTP (app password) and/or Brevo |
| Jobs (optional) | Celery + Redis |
| Deploy | Vercel (frontend), Render (backend), Supabase (DB) |

---

## Project layout

```text
jobhunter/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry
│   │   ├── config.py            # Settings from env
│   │   ├── database.py
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic DTOs
│   │   ├── routers/             # HTTP routes under /api
│   │   ├── scrapers/            # Job board clients
│   │   ├── services/            # Auth, scrape, apply, match, email
│   │   ├── tasks/               # Celery tasks
│   │   └── utils/               # CV parse, apply extract, PDF helpers
│   ├── alembic/                 # Migrations
│   ├── scripts/                 # migrate.sh, check_db.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                     # Local secrets (not committed)
├── frontend/
│   ├── src/
│   │   ├── api/client.js        # API base URL + fetch helpers
│   │   ├── pages/               # Search, Matches, Queue, CV, …
│   │   ├── components/
│   │   └── store/AuthContext.jsx
│   ├── .env.local               # Local Vite env
│   └── .env.production          # Production API URL template
├── vercel.json
└── README.md
```

---

## Quick start (local)

### Prerequisites

- Python 3.11+  
- Node.js 18+  
- (Optional) Redis for Celery  
- (Optional) Supabase / Postgres for a shared DB  

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and edit env
cp .env.example .env              # or create .env from the section below

# Local SQLite works with zero extra setup:
# DATABASE_URL=sqlite:///./jobhunter.db

# Run API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### 2. Frontend

```bash
cd frontend
npm install
# Ensure .env.local has:
# VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

- App: http://localhost:5173  

### 3. First use

1. Register an account  
2. **CV** → upload PDF/DOCX → re-parse  
3. **Search** → **Scrape now**  
4. **Matches** → open a role → track or **Apply by email**  
5. **Queue** → review drafts / email status  

---

## Environment variables

### Backend (`backend/.env`)

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | DB connection | `sqlite:///./jobhunter.db` or Supabase Postgres URI |
| `SECRET_KEY` | JWT signing | long random string |
| `DEBUG` | Verbose mode | `true` / `false` |
| `CORS_ORIGINS` | Allowed browser origins (comma-separated, **no trailing slash**) | `http://localhost:5173,https://your-app.vercel.app` |
| `CORS_ORIGIN_REGEX` | Extra origin pattern | `https://.*\.vercel\.app` |
| `EMAIL_PROVIDER` | `auto` \| `smtp` \| `brevo` \| `dry_run` | `auto` |
| `EMAIL_FROM` | From address | your Gmail or verified Brevo sender |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Gmail app password SMTP | `smtp.gmail.com`, `587`, … |
| `BREVO_API_KEY` | Brevo transactional email | from Brevo dashboard |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Optional Adzuna scrape | developer.adzuna.com |
| `AUTO_SCRAPE_ENABLED` | In-process scrape scheduler | `true` |
| `AUTO_SCRAPE_INTERVAL_HOURS` | Scrape period | `6` |
| `AUTO_SCRAPE_ON_STARTUP` | Scrape when API boots | `false` |
| `AUTO_SCRAPE_SOURCES` | Comma list, empty = all free | `remoteok,remotive,jobicy` |
| `AUTO_SCRAPE_LIMIT_PER_SOURCE` | Cap per board | `40` |

See `backend/.env.example` for a fuller template.

### Frontend

| Variable | Where | Purpose |
|----------|--------|---------|
| `VITE_API_BASE_URL` | `.env.local` (dev) / Vercel env (prod) | Backend origin, **no trailing slash** |

Examples:

```env
# Local
VITE_API_BASE_URL=http://localhost:8000

# Production
VITE_API_BASE_URL=https://your-api.onrender.com
```

> **Important:** Vite inlines `VITE_*` at **build** time. After changing the variable on Vercel, **redeploy** the frontend.

---

## Database & migrations

### Local SQLite

Default. Tables are created on API startup (`create_all` + light SQLite patches).

### Supabase / Postgres (live)

1. Supabase → **Project Settings** → **Database** → connection URI  
2. Set `DATABASE_URL` (include `?sslmode=require`; URL-encode special characters in the password)  
3. Run migrations:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
python scripts/check_db.py
```

Useful commands:

```bash
alembic current
alembic history
alembic revision --autogenerate -m "describe change"   # review file, then upgrade
./scripts/migrate.sh
```

Initial migration: `backend/alembic/versions/001_initial_schema.py`  
Tables: `users`, `jobs`, `cvs`, `saved_searches`, `applications`, `alembic_version`.

---

## API overview

Base path: `/api`  
Interactive docs: `/docs`

| Area | Examples |
|------|----------|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Jobs | `GET /api/jobs`, `POST /api/jobs/scrape`, `GET /api/jobs/sources` |
| Scrape | `GET /api/jobs/scrape/status`, `POST /api/jobs/scrape/run-scheduled` |
| CV | `GET/PUT /api/cv`, `POST /api/cv/upload`, `POST /api/cv/parse`, `GET /api/cv/matches` |
| Apply | `POST /api/apply/draft`, `POST /api/apply/send/{id}`, `GET /api/apply/queue` |
| Email | `GET /api/apply/email-status`, `POST /api/apply/test-email` |
| Tracker | `GET/POST /api/tracker`, statuses include `wishlist`, `draft`, `applied`, … |
| Health | `GET /health` |

Protected routes expect:

```http
Authorization: Bearer <access_token>
```

---

## Job sources

| Source | Key required? |
|--------|----------------|
| `remoteok` | No |
| `remotive` | No |
| `arbeitnow` | No |
| `jobicy` | No |
| `himalayas` | No |
| `themuse` | No |
| `adzuna` | Yes (`ADZUNA_*`) |

Scrapers normalize listings into one schema and detect `apply_method` (`email` \| `url` \| `unknown`) when possible.

### Auto-scrape

- **In-process** (default with the API): controlled by `AUTO_SCRAPE_*`  
- **Celery** (optional, multi-worker production):

```bash
# Redis running
celery -A app.tasks.celery_app.celery_app worker -l info
celery -A app.tasks.celery_app.celery_app beat -l info
```

Beat schedule includes periodic scrape, alerts, and auto-apply tasks.

---

## Email applications

1. Prefer **Gmail App Password** (`EMAIL_PROVIDER=smtp` or `auto` with `SMTP_PASSWORD` set).  
2. Or **Brevo** with a verified `EMAIL_FROM` sender.  
3. Without either provider, sends are **dry-run** (logged, marked applied for local testing).  

Apply flow:

- Attach **uploaded CV file** when present (not a regenerated profile PDF)  
- Body does **not** append a job listing URL  
- One application row per user + job (draft upsert is race-safe)  

Use **Queue → Outbound email → Send test email** to verify delivery.

---

## Production deploy

### Backend (e.g. Render)

1. Connect the repo; root directory `backend` (or use `Dockerfile`)  
2. Start command:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

3. Set env: `DATABASE_URL`, `SECRET_KEY`, **`CORS_ORIGINS`**, email vars, etc.  
4. Run `alembic upgrade head` once (Render shell or release command)  

**CORS must list your Vercel origin** (no trailing slash):

```env
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
CORS_ORIGIN_REGEX=https://.*\.vercel\.app
```

If the browser shows CORS errors while `/health` works, the origin list is almost always wrong or the service was not restarted after changing env.

### Frontend (Vercel)

1. Root: `frontend` (or monorepo with framework Vite)  
2. Env:

   ```env
   VITE_API_BASE_URL=https://your-api.onrender.com
   ```

3. Redeploy after any change to `VITE_*`  

### Why “frontend can’t see backend”

| Check | Expected |
|-------|----------|
| Backend health | `GET https://api…/health` → `{"status":"ok"}` |
| Frontend API base | Built JS calls Render URL, **not** `localhost` |
| CORS | `access-control-allow-origin` includes the Vercel origin |
| Mixed content | Both sites **HTTPS** |

Separate Vercel + Render deploys do **not** rely on `vercel.json` service rewrites for cross-host API calls; CORS + `VITE_API_BASE_URL` do.

---

## Frontend routes

| Path | Description |
|------|-------------|
| `/` | Job search + scrape controls |
| `/matches` | CV-ranked jobs |
| `/queue` | Email drafts, send, auto-apply settings |
| `/saved` | Saved searches & alerts |
| `/tracker` | Application pipeline |
| `/cv` | Profile, upload, parse, export |
| `/login` | Sign in / register |

Mobile: hamburger drawer for navigation.

---

## Development tips

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# New migration after model changes
cd backend && alembic revision --autogenerate -m "msg"
# review alembic/versions/* then:
alembic upgrade head
```

- Never commit `.env` or secrets (see root `.gitignore`).  
- Rotate any keys that have been shared in chat or screenshots.  
- Respect each job board’s terms; prefer official/public APIs.  

---

## License / intent

Built as a personal job-hunting tool. Use scraped data and outbound email responsibly (rate limits, accurate recipients, no spam).

---

## Quick troubleshooting

| Symptom | Likely fix |
|---------|------------|
| CORS / “Failed to fetch” in browser | Set `CORS_ORIGINS` on API to exact Vercel URL; redeploy/restart API |
| Frontend still hits localhost | Set `VITE_API_BASE_URL` on Vercel and **redeploy** |
| DB connection errors on Render | Check Supabase `DATABASE_URL`, SSL, URL-encoded password |
| Empty schema on Postgres | `alembic upgrade head` |
| Email “applied” but nothing arrives | Configure SMTP/Brevo; check spam; verify recipient exists |
| Draft 500 unique constraint | Fixed via upsert; update backend and retry |
| Scrape returns little data | Network limits, source downtime; try **Scrape now** and check source filter |

For interactive API exploration, use **http://localhost:8000/docs** (or your deployed `/docs`).
