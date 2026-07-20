"""Scheduled scraping task."""

from app.database import SessionLocal
from app.services.job_aggregator import JobAggregator
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.scrape_task.scrape_all_jobs")
def scrape_all_jobs(query: str | None = None, limit_per_source: int = 50) -> dict:
    db = SessionLocal()
    try:
        result = JobAggregator().scrape_and_store(
            db,
            query=query,
            sources=None,
            limit_per_source=limit_per_source,
        )
        return result
    finally:
        db.close()
