"""RemoteOK scraper client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

REMOTEOK_URL = "https://remoteok.com/api"


class RemoteOKScraper(BaseScraper):
    name = "remoteok"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        headers = {
            "User-Agent": "JobHunter/1.0 (local dev; educational)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(REMOTEOK_URL)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        q = (query or "").lower().strip()

        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                # First element is often legal metadata
                continue
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
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        posted_at = None
        epoch = item.get("epoch") or item.get("date")
        if isinstance(epoch, (int, float)):
            posted_at = datetime.fromtimestamp(epoch, tz=timezone.utc).replace(tzinfo=None)
        elif isinstance(epoch, str) and epoch.isdigit():
            posted_at = datetime.fromtimestamp(int(epoch), tz=timezone.utc).replace(tzinfo=None)

        slug = item.get("slug") or item.get("id")
        url = item.get("url") or (f"https://remoteok.com/remote-jobs/{slug}" if slug else None)

        return ScrapedJob(
            external_id=str(item.get("id")),
            source=self.name,
            title=item.get("position") or item.get("title") or "Untitled",
            company=item.get("company"),
            location=item.get("location") or "Remote",
            description=item.get("description") or item.get("company_description"),
            url=url,
            salary_min=_to_float(item.get("salary_min")),
            salary_max=_to_float(item.get("salary_max")),
            currency="USD",
            tags=[str(t) for t in tags],
            is_remote=True,
            posted_at=posted_at,
            raw=item,
        )


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
