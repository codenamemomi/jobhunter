"""Tracker / apply-queue schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobOut


class ApplicationCreate(BaseModel):
    job_id: int
    status: str = Field(default="wishlist")
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    email_subject: str | None = None
    email_body: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    status: str
    notes: str | None = None
    applied_at: datetime | None = None
    updated_at: datetime
    created_at: datetime
    apply_channel: str | None = None
    email_to: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    match_score: float | None = None
    sent_at: datetime | None = None
    send_error: str | None = None
    is_auto: bool = False
    job: JobOut | None = None


class DraftCreate(BaseModel):
    job_id: int
    subject: str | None = None
    body: str | None = None
    match_score: float | None = None


class DraftUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    notes: str | None = None


class SendRequest(BaseModel):
    attach_cv: bool = True


class AutoSettingsUpdate(BaseModel):
    auto_draft_enabled: bool | None = None
    auto_send_enabled: bool | None = None
    auto_min_score: float | None = Field(default=None, ge=0, le=100)
    auto_daily_limit: int | None = Field(default=None, ge=0, le=50)
    auto_prefer_remote: bool | None = None
    auto_email_only: bool | None = None


class AutoSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    auto_draft_enabled: bool = False
    auto_send_enabled: bool = False
    auto_min_score: float = 75.0
    auto_daily_limit: int = 5
    auto_prefer_remote: bool = True
    auto_email_only: bool = True
    sent_today: int = 0
