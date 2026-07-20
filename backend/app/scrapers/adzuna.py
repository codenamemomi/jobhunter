"""Adzuna scraper client."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.scrapers.base import BaseScraper, ScrapedJob


class AdzunaScraper(BaseScraper):
    """Requires ADZUNA_APP_ID and ADZUNA_APP_KEY. Returns [] if not configured."""

    name = "adzuna"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            return []

        country = settings.adzuna_country or "gb"
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "results_per_page": min(limit, 50),
            "content-type": "application/json",
        }
        if query:
            params["what"] = query

        headers = {"User-Agent": "JobHunter/1.0 (local dev; educational)"}
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        for item in data.get("results") or []:
            jobs.append(self._normalize(item))
            if len(jobs) >= limit:
                break
        return jobs

    def _normalize(self, item: dict[str, Any]) -> ScrapedJob:
        location = None
        loc = item.get("location") or {}
        if isinstance(loc, dict):
            location = loc.get("display_name")
        elif isinstance(loc, str):
            location = loc

        company = None
        comp = item.get("company") or {}
        if isinstance(comp, dict):
            company = comp.get("display_name")
        elif isinstance(comp, str):
            company = comp

        posted_at = None
        created = item.get("created")
        if created:
            try:
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                posted_at = None

        category = item.get("category") or {}
        tags: list[str] = []
        if isinstance(category, dict) and category.get("label"):
            tags.append(str(category["label"]))

        title = item.get("title") or "Untitled"
        is_remote = "remote" in title.lower() or (location or "").lower().find("remote") >= 0

        return ScrapedJob(
            external_id=str(item.get("id")),
            source=self.name,
            title=title,
            company=company,
            location=location,
            description=item.get("description"),
            url=item.get("redirect_url"),
            salary_min=_to_float(item.get("salary_min")),
            salary_max=_to_float(item.get("salary_max")),
            currency="GBP" if settings.adzuna_country == "gb" else None,
            tags=tags,
            is_remote=is_remote,
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
