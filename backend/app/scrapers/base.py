"""Base scraper abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScrapedJob:
    """Normalized job payload returned by every scraper."""

    external_id: str
    source: str
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    url: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    tags: list[str] = field(default_factory=list)
    is_remote: bool = False
    posted_at: datetime | None = None
    raw: dict[str, Any] | None = None

    def tags_csv(self) -> str | None:
        if not self.tags:
            return None
        return ",".join(sorted({t.strip() for t in self.tags if t and t.strip()}))


class BaseScraper(ABC):
    """Interface for job source scrapers."""

    name: str = "base"

    @abstractmethod
    def fetch(self, query: str | None = None, limit: int = 50) -> list[ScrapedJob]:
        """Fetch and normalize jobs from the remote source."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
