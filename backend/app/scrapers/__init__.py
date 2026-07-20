"""Scraper clients."""

from app.scrapers.adzuna import AdzunaScraper
from app.scrapers.arbeitnow import ArbeitNowScraper
from app.scrapers.base import BaseScraper, ScrapedJob
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.remotive import RemotiveScraper

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "remoteok": RemoteOKScraper,
    "remotive": RemotiveScraper,
    "arbeitnow": ArbeitNowScraper,
    "adzuna": AdzunaScraper,
}


def get_scraper(name: str) -> BaseScraper:
    key = name.lower().strip()
    if key not in SCRAPER_REGISTRY:
        raise ValueError(f"Unknown scraper: {name}. Choose from {list(SCRAPER_REGISTRY)}")
    return SCRAPER_REGISTRY[key]()


def get_all_scrapers(include_keyed: bool = True) -> list[BaseScraper]:
    scrapers: list[BaseScraper] = [
        RemoteOKScraper(),
        RemotiveScraper(),
        ArbeitNowScraper(),
    ]
    if include_keyed:
        scrapers.append(AdzunaScraper())
    return scrapers


__all__ = [
    "BaseScraper",
    "ScrapedJob",
    "RemoteOKScraper",
    "RemotiveScraper",
    "ArbeitNowScraper",
    "AdzunaScraper",
    "SCRAPER_REGISTRY",
    "get_scraper",
    "get_all_scrapers",
]
