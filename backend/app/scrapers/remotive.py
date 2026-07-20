"""Remotive scraper client."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveScraper(BaseScraper):
    name = "remotive"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["search"] = query

        headers = {
            "User-Agent": "JobHunter/1.0 (local dev; educational)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(REMOTIVE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        for item in data.get("jobs") or []:
            jobs.append(self._normalize(item))
            if len(jobs) >= limit:
                break
        return jobs

    def _normalize(self, item: dict[str, Any]) -> ScrapedJob:
        tags = item.get("tags") or []
        category = item.get("category")
        if category:
            tags = list(tags) + [category]

        posted_at = None
        pub = item.get("publication_date")
        if pub:
            try:
                posted_at = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                posted_at = None

        return ScrapedJob(
            external_id=str(item.get("id")),
            source=self.name,
            title=item.get("title") or "Untitled",
            company=item.get("company_name"),
            location=item.get("candidate_required_location") or "Remote",
            description=item.get("description"),
            url=item.get("url"),
            tags=[str(t) for t in tags if t],
            is_remote=True,
            posted_at=posted_at,
            raw=item,
        )
