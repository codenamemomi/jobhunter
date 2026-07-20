"""Job schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
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
    tags: str | None = None
    is_remote: bool = False
    posted_at: datetime | None = None
    scraped_at: datetime


class JobSearchParams(BaseModel):
    q: str | None = None
    location: str | None = None
    source: str | None = None
    is_remote: bool | None = None
    company: str | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class ScrapeRequest(BaseModel):
    query: str | None = None
    sources: list[str] | None = None  # None = all free sources
    limit_per_source: int = Field(default=50, ge=1, le=100)


class ScrapeResult(BaseModel):
    sources: dict[str, int]
    total_fetched: int
    total_new: int
    total_updated: int
