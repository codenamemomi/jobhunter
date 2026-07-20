"""CV schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import JobOut


class CVUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    experience: str | None = None
    education: str | None = None
    skills: str | None = None
    links: str | None = None


class CVOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    experience: str | None = None
    education: str | None = None
    skills: str | None = None
    links: str | None = None
    original_filename: str | None = None
    parsed_skills: str | None = None
    parsed_titles: str | None = None
    parsed_keywords: str | None = None
    parsed_at: datetime | None = None
    has_raw_text: bool = False
    updated_at: datetime
    created_at: datetime

    @classmethod
    def from_model(cls, cv) -> "CVOut":
        return cls(
            id=cv.id,
            user_id=cv.user_id,
            full_name=cv.full_name,
            headline=cv.headline,
            email=cv.email,
            phone=cv.phone,
            location=cv.location,
            summary=cv.summary,
            experience=cv.experience,
            education=cv.education,
            skills=cv.skills,
            links=cv.links,
            original_filename=cv.original_filename,
            parsed_skills=cv.parsed_skills,
            parsed_titles=cv.parsed_titles,
            parsed_keywords=cv.parsed_keywords,
            parsed_at=cv.parsed_at,
            has_raw_text=bool(cv.raw_text),
            updated_at=cv.updated_at,
            created_at=cv.created_at,
        )


class JobMatchOut(BaseModel):
    job: JobOut
    score: float = Field(description="Match score 0–100")
    matched_skills: list[str] = []
    matched_titles: list[str] = []
    reasons: list[str] = []


class MatchResponse(BaseModel):
    profile_skills: list[str]
    profile_titles: list[str]
    total_candidates_scanned: int | None = None
    matches: list[JobMatchOut]
