"""Saved search schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    query: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    tags: str | None = None
    source: str | None = None
    alerts_enabled: bool = True


class SavedSearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    query: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    tags: str | None = None
    source: str | None = None
    alerts_enabled: bool | None = None


class SavedSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    query: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    tags: str | None = None
    source: str | None = None
    alerts_enabled: bool
    last_alerted_at: datetime | None = None
    created_at: datetime
