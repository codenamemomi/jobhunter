"""In-process auto-scrape scheduler (no Celery required)."""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from app.config import settings
from app.database import SessionLocal
from app.services.job_aggregator import JobAggregator

logger = logging.getLogger(__name__)


class ScrapeScheduler:
    """Background thread that scrapes on an interval while the API is running."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.last_run_at: datetime | None = None
        self.last_result: dict[str, Any] | None = None
        self.last_error: str | None = None
        self.is_running: bool = False
        self.next_run_at: datetime | None = None

    @property
    def enabled(self) -> bool:
        return bool(settings.auto_scrape_enabled)

    @property
    def interval_seconds(self) -> int:
        hours = max(float(settings.auto_scrape_interval_hours or 6), 0.25)
        return int(hours * 3600)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval_hours": settings.auto_scrape_interval_hours,
            "interval_seconds": self.interval_seconds,
            "thread_alive": bool(self._thread and self._thread.is_alive()),
            "is_scraping_now": self.is_running,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_error": self.last_error,
            "last_result": self.last_result,
            "run_on_startup": settings.auto_scrape_on_startup,
            "limit_per_source": settings.auto_scrape_limit_per_source,
            "query": settings.auto_scrape_query or None,
            "sources": settings.auto_scrape_sources_list or None,
            "note": (
                "In-app scheduler runs inside uvicorn. "
                "For multi-worker production, prefer Celery beat instead."
            ),
        }

    def start(self) -> None:
        if not self.enabled:
            logger.info("Auto-scrape disabled (AUTO_SCRAPE_ENABLED=false)")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="jobhunter-auto-scrape",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Auto-scrape started: every %sh, on_startup=%s",
            settings.auto_scrape_interval_hours,
            settings.auto_scrape_on_startup,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("Auto-scrape stopped")

    def run_once(self, *, force: bool = False) -> dict[str, Any]:
        """Run a scrape now (used by scheduler and API)."""
        with self._lock:
            if self.is_running and not force:
                return {"status": "busy", "message": "Scrape already in progress"}
            self.is_running = True
            self.last_error = None

        try:
            db = SessionLocal()
            try:
                sources = settings.auto_scrape_sources_list or None
                result = JobAggregator().scrape_and_store(
                    db,
                    query=settings.auto_scrape_query or None,
                    sources=sources,
                    limit_per_source=int(settings.auto_scrape_limit_per_source or 40),
                )
                self.last_result = result
                self.last_run_at = datetime.utcnow()
                logger.info("Auto-scrape finished: %s", result)
                return {"status": "ok", **result}
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.exception("Auto-scrape failed")
            return {"status": "error", "detail": str(exc)}
        finally:
            self.is_running = False

    def _loop(self) -> None:
        # Optional immediate run
        if settings.auto_scrape_on_startup:
            self.run_once()
        while not self._stop.is_set():
            wait = self.interval_seconds
            self.next_run_at = datetime.utcnow()
            # rough next time after wait (updated after each run too)
            from datetime import timedelta

            self.next_run_at = datetime.utcnow() + timedelta(seconds=wait)
            if self._stop.wait(timeout=wait):
                break
            self.run_once()
            self.next_run_at = datetime.utcnow() + timedelta(seconds=self.interval_seconds)


scrape_scheduler = ScrapeScheduler()
