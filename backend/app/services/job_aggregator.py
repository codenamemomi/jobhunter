"""Job aggregation service."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.job import Job
from app.scrapers import SCRAPER_REGISTRY, get_all_scrapers, get_scraper
from app.scrapers.base import ScrapedJob
from app.utils.apply_extractor import extract_apply_info
from app.utils.deduplicator import job_content_hash

logger = logging.getLogger(__name__)


class JobAggregator:
    """Fetch from scrapers and upsert into the jobs table."""

    def scrape_and_store(
        self,
        db: Session,
        *,
        query: str | None = None,
        sources: list[str] | None = None,
        limit_per_source: int = 50,
    ) -> dict:
        if sources:
            scrapers = []
            for name in sources:
                try:
                    scrapers.append(get_scraper(name))
                except ValueError as exc:
                    logger.warning("%s", exc)
        else:
            scrapers = get_all_scrapers(include_keyed=True)

        per_source: dict[str, int] = {}
        total_new = 0
        total_updated = 0
        total_fetched = 0
        email_apply = 0

        for scraper in scrapers:
            try:
                scraped = scraper.fetch(query=query, limit=limit_per_source)
            except Exception:  # noqa: BLE001
                logger.exception("Scraper %s failed", scraper.name)
                per_source[scraper.name] = 0
                continue

            per_source[scraper.name] = len(scraped)
            total_fetched += len(scraped)

            for item in scraped:
                created, updated, is_email = self._upsert_job(db, item)
                total_new += int(created)
                total_updated += int(updated)
                email_apply += int(is_email)

        db.commit()
        return {
            "sources": per_source,
            "total_fetched": total_fetched,
            "total_new": total_new,
            "total_updated": total_updated,
            "email_apply_count": email_apply,
        }

    def backfill_apply_info(self, db: Session, limit: int = 500) -> int:
        """Re-extract apply info for existing jobs (migration helper)."""
        jobs = (
            db.query(Job)
            .filter((Job.apply_method.is_(None)) | (Job.apply_method == "unknown") | (Job.apply_email.is_(None)))
            .order_by(Job.scraped_at.desc())
            .limit(limit)
            .all()
        )
        updated = 0
        for job in jobs:
            info = extract_apply_info(job.description, job.url, None)
            job.apply_method = info.apply_method
            job.apply_email = info.apply_email
            job.apply_url = info.apply_url or job.url
            updated += 1
        db.commit()
        return updated

    def _upsert_job(self, db: Session, item: ScrapedJob) -> tuple[bool, bool, bool]:
        existing = (
            db.query(Job)
            .filter(Job.source == item.source, Job.external_id == item.external_id)
            .first()
        )
        content_hash = job_content_hash(item.title, item.company, item.location, item.source)
        tags = item.tags_csv()
        apply = extract_apply_info(item.description, item.url, item.raw)

        if existing is None:
            job = Job(
                external_id=item.external_id,
                source=item.source,
                title=item.title,
                company=item.company,
                location=item.location,
                description=item.description,
                url=item.url,
                salary_min=item.salary_min,
                salary_max=item.salary_max,
                currency=item.currency,
                tags=tags,
                is_remote=item.is_remote,
                posted_at=item.posted_at,
                scraped_at=datetime.utcnow(),
                content_hash=content_hash,
                apply_method=apply.apply_method,
                apply_email=apply.apply_email,
                apply_url=apply.apply_url,
            )
            db.add(job)
            return True, False, apply.apply_method == "email"

        existing.title = item.title
        existing.company = item.company
        existing.location = item.location
        existing.description = item.description
        existing.url = item.url
        existing.salary_min = item.salary_min
        existing.salary_max = item.salary_max
        existing.currency = item.currency
        existing.tags = tags
        existing.is_remote = item.is_remote
        existing.posted_at = item.posted_at or existing.posted_at
        existing.scraped_at = datetime.utcnow()
        existing.content_hash = content_hash
        existing.apply_method = apply.apply_method
        existing.apply_email = apply.apply_email
        existing.apply_url = apply.apply_url
        return False, True, apply.apply_method == "email"


def available_sources() -> list[str]:
    return list(SCRAPER_REGISTRY.keys())
