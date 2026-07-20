"""Scraper clients."""

from app.scrapers.adzuna import AdzunaScraper
from app.scrapers.arbeitnow import ArbeitNowScraper
from app.scrapers.base import BaseScraper, ScrapedJob
from app.scrapers.himalayas import HimalayasScraper
from app.scrapers.jobicy import JobicyScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.remotive import RemotiveScraper
from app.scrapers.themuse import TheMuseScraper

# Free public sources (no API key)
FREE_SCRAPERS: dict[str, type[BaseScraper]] = {
    "remoteok": RemoteOKScraper,
    "remotive": RemotiveScraper,
    "arbeitnow": ArbeitNowScraper,
    "jobicy": JobicyScraper,
    "himalayas": HimalayasScraper,
    "themuse": TheMuseScraper,
}

# Optional key-based sources
KEYED_SCRAPERS: dict[str, type[BaseScraper]] = {
    "adzuna": AdzunaScraper,
}

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {**FREE_SCRAPERS, **KEYED_SCRAPERS}


def get_scraper(name: str) -> BaseScraper:
    key = name.lower().strip()
    if key not in SCRAPER_REGISTRY:
        raise ValueError(f"Unknown scraper: {name}. Choose from {list(SCRAPER_REGISTRY)}")
    return SCRAPER_REGISTRY[key]()


def get_all_scrapers(include_keyed: bool = True) -> list[BaseScraper]:
    scrapers: list[BaseScraper] = [cls() for cls in FREE_SCRAPERS.values()]
    if include_keyed:
        scrapers.extend(cls() for cls in KEYED_SCRAPERS.values())
    return scrapers


def source_catalog() -> list[dict]:
    """Metadata for UI / status endpoints."""
    rows = []
    for name in FREE_SCRAPERS:
        rows.append({"name": name, "requires_key": False, "enabled": True})
    for name in KEYED_SCRAPERS:
        rows.append(
            {
                "name": name,
                "requires_key": True,
                "enabled": name == "adzuna",  # still listed; may return [] without keys
            }
        )
    return rows


__all__ = [
    "BaseScraper",
    "ScrapedJob",
    "RemoteOKScraper",
    "RemotiveScraper",
    "ArbeitNowScraper",
    "JobicyScraper",
    "HimalayasScraper",
    "TheMuseScraper",
    "AdzunaScraper",
    "SCRAPER_REGISTRY",
    "FREE_SCRAPERS",
    "KEYED_SCRAPERS",
    "get_scraper",
    "get_all_scrapers",
    "source_catalog",
]
