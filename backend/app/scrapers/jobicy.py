"""Jobicy remote jobs API scraper (free, no key)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicyScraper(BaseScraper):
    name = "jobicy"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        params: dict[str, Any] = {"count": min(limit, 50)}
        if query:
            params["tag"] = query

        headers = {
            "User-Agent": "JobHunter/1.0 (local; educational)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(JOBICY_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        q = (query or "").lower().strip()
        for item in data.get("jobs") or []:
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
        tags: list[str] = []
        for key in ("jobIndustry", "jobType", "jobLevel"):
            val = item.get(key)
            if isinstance(val, list):
                tags.extend(str(v) for v in val if v)
            elif val:
                tags.append(str(val))

        posted_at = None
        pub = item.get("pubDate")
        if pub:
            try:
                posted_at = datetime.fromisoformat(str(pub).replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                posted_at = None

        geo = item.get("jobGeo") or "Remote"
        return ScrapedJob(
            external_id=str(item.get("id") or item.get("url") or item.get("jobTitle")),
            source=self.name,
            title=item.get("jobTitle") or "Untitled",
            company=item.get("companyName"),
            location=geo if isinstance(geo, str) else "Remote",
            description=item.get("jobDescription") or item.get("jobExcerpt"),
            url=item.get("url") or item.get("jobUrl"),
            tags=tags,
            is_remote=True,
            posted_at=posted_at,
            raw=item,
        )
