"""Himalayas remote jobs API scraper (free public JSON)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScrapedJob

HIMALAYAS_URL = "https://himalayas.app/jobs/api"


class HimalayasScraper(BaseScraper):
    name = "himalayas"

    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        headers = {
            "User-Agent": "JobHunter/1.0 (local; educational)",
            "Accept": "application/json",
        }
        with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
            # API supports limit & offset
            resp = client.get(HIMALAYAS_URL, params={"limit": min(limit, 100)})
            resp.raise_for_status()
            data = resp.json()

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("jobs") or data.get("data") or []
        else:
            items = []
        if not isinstance(items, list):
            items = []

        jobs: list[ScrapedJob] = []
        q = (query or "").lower().strip()
        for item in items:
            if not isinstance(item, dict):
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
        tags: list[str] = []
        for key in ("categories", "parentCategories", "skills", "tags"):
            val = item.get(key)
            if isinstance(val, list):
                for v in val:
                    if isinstance(v, dict):
                        tags.append(str(v.get("name") or v.get("title") or ""))
                    elif v:
                        tags.append(str(v))

        company = item.get("companyName") or item.get("company")
        if isinstance(company, dict):
            company = company.get("name")

        restrictions = item.get("locationRestrictions") or []
        if isinstance(restrictions, list) and restrictions:
            location = ", ".join(str(x) for x in restrictions[:4])
        else:
            location = "Remote"

        posted_at = None
        for key in ("pubDate", "publishedDate", "created_at", "publishedAt", "updatedAt"):
            raw = item.get(key)
            if raw is None:
                continue
            if isinstance(raw, (int, float)):
                ts = raw / 1000 if raw > 1e12 else raw
                try:
                    posted_at = datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
                except (OSError, ValueError, OverflowError):
                    posted_at = None
            elif isinstance(raw, str):
                try:
                    posted_at = datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(
                        tzinfo=None
                    )
                except ValueError:
                    posted_at = None
            if posted_at:
                break

        slug = item.get("slug") or item.get("guid")
        company_slug = item.get("companySlug") or ""
        url = item.get("applicationLink") or item.get("url")
        if not url and slug:
            url = f"https://himalayas.app/companies/{company_slug}/jobs/{slug}" if company_slug else f"https://himalayas.app/jobs/{slug}"
        ext = str(item.get("id") or slug or url or item.get("title"))

        salary_min = item.get("minSalary")
        salary_max = item.get("maxSalary")
        try:
            salary_min = float(salary_min) if salary_min is not None else None
            salary_max = float(salary_max) if salary_max is not None else None
        except (TypeError, ValueError):
            salary_min = salary_max = None

        return ScrapedJob(
            external_id=ext,
            source=self.name,
            title=item.get("title") or item.get("jobTitle") or "Untitled",
            company=str(company) if company else None,
            location=str(location),
            description=item.get("description") or item.get("excerpt"),
            url=url,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=item.get("currency"),
            tags=[t for t in tags if t],
            is_remote=True,
            posted_at=posted_at,
            raw=item,
        )
