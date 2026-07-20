"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import alerts, apply, auth, cv, jobs, searches, tracker


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_prefix
app.include_router(auth.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)
app.include_router(searches.router, prefix=prefix)
app.include_router(tracker.router, prefix=prefix)
app.include_router(cv.router, prefix=prefix)
app.include_router(alerts.router, prefix=prefix)
app.include_router(apply.router, prefix=prefix)


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": prefix,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
