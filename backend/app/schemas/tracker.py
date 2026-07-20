"""Tracker schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.tracker import APPLICATION_STATUSES
from app.schemas.job import JobOut


class ApplicationCreate(BaseModel):
    job_id: int
    status: str = Field(default="wishlist")
    notes: str | None = None

    def validate_status(self) -> "ApplicationCreate":
        if self.status not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
        return self


class ApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


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
    job: JobOut | None = None
