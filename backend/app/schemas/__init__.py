"""Pydantic schemas."""

from app.schemas.cv import CVOut, CVUpdate
from app.schemas.job import JobOut, JobSearchParams, ScrapeRequest, ScrapeResult
from app.schemas.saved_search import SavedSearchCreate, SavedSearchOut, SavedSearchUpdate
from app.schemas.tracker import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserOut",
    "Token",
    "JobOut",
    "JobSearchParams",
    "ScrapeRequest",
    "ScrapeResult",
    "SavedSearchCreate",
    "SavedSearchUpdate",
    "SavedSearchOut",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationOut",
    "CVUpdate",
    "CVOut",
]
