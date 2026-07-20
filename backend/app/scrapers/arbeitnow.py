"""ArbeitNow scraper client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitNowScraper(BaseScraper):
    name = "arbeitnow"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        headers = {
            "User-Agent": "JobHunter/1.0 (local dev; educational)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(ARBEITNOW_URL)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        q = (query or "").lower().strip()

        for item in data.get("data") or []:
            job = self._normalize(item)
            if q and q not in " ".join(
                filter(None, [job.title, job.company or "", job.description or "", " ".join(job.tags)])
            ).lower():
                continue
            jobs.append(job)
            if len(jobs) >= limit:
                break
        return jobs

    def _normalize(self, item: dict[str, Any]) -> ScrapedJob:
        tags = item.get("tags") or []
        job_types = item.get("job_types") or []
        all_tags = [str(t) for t in list(tags) + list(job_types) if t]

        posted_at = None
        created = item.get("created_at")
        if isinstance(created, (int, float)):
            posted_at = datetime.fromtimestamp(created, tz=timezone.utc).replace(tzinfo=None)

        return ScrapedJob(
            external_id=str(item.get("slug") or item.get("url") or item.get("title")),
            source=self.name,
            title=item.get("title") or "Untitled",
            company=item.get("company_name"),
            location=item.get("location"),
            description=item.get("description"),
            url=item.get("url"),
            tags=all_tags,
            is_remote=bool(item.get("remote")),
            posted_at=posted_at,
            raw=item,
        )
