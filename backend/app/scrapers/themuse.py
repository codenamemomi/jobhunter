"""The Muse public jobs API scraper (free, no key)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

THEMUSE_URL = "https://www.themuse.com/api/public/jobs"


class TheMuseScraper(BaseScraper):
    name = "themuse"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        headers = {
            "User-Agent": "JobHunter/1.0 (local; educational)",
            "Accept": "application/json",
        }
        jobs: list[ScrapedJob] = []
        page = 0
        q = (query or "").lower().strip()

        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            while len(jobs) < limit and page < 5:
                params: dict[str, Any] = {"page": page}
                if query:
                    params["category"] = query  # Muse uses categories; still filters client-side
                resp = client.get(THEMUSE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results") or []
                if not results:
                    break
                for item in results:
                    job = self._normalize(item)
                    if q and q not in " ".join(
                        filter(
                            None,
                            [job.title, job.company or "", job.description or "", " ".join(job.tags)],
                        )
                    ).lower():
                        continue
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
                page += 1
        return jobs

    def _normalize(self, item: dict[str, Any]) -> ScrapedJob:
        company = None
        comp = item.get("company") or {}
        if isinstance(comp, dict):
            company = comp.get("name")

        locations = item.get("locations") or []
        location_parts = []
        for loc in locations:
            if isinstance(loc, dict) and loc.get("name"):
                location_parts.append(loc["name"])
        location = ", ".join(location_parts) if location_parts else None

        cats = item.get("categories") or []
        levels = item.get("levels") or []
        tags: list[str] = []
        for c in cats:
            if isinstance(c, dict) and c.get("name"):
                tags.append(c["name"])
        for lv in levels:
            if isinstance(lv, dict) and lv.get("name"):
                tags.append(lv["name"])

        posted_at = None
        pub = item.get("publication_date")
        if pub:
            try:
                posted_at = datetime.fromisoformat(str(pub).replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                posted_at = None

        refs = item.get("refs") or {}
        url = refs.get("landing_page") if isinstance(refs, dict) else None

        is_remote = False
        if location and "remote" in location.lower():
            is_remote = True
        if any("remote" in (t or "").lower() for t in tags):
            is_remote = True

        return ScrapedJob(
            external_id=str(item.get("id")),
            source=self.name,
            title=item.get("name") or "Untitled",
            company=company,
            location=location,
            description=item.get("contents"),
            url=url,
            tags=tags,
            is_remote=is_remote,
            posted_at=posted_at,
            raw=item,
        )
