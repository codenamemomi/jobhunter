"""Job-related routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobOut, ScrapeRequest, ScrapeResult
from app.services.auth_service import get_current_user
from app.services.job_aggregator import JobAggregator, available_sources
from app.utils.filters import apply_job_filters

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
def list_jobs(
    q: str | None = None,
    location: str | None = None,
    source: str | None = None,
    is_remote: bool | None = None,
    company: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Job]:
    query = db.query(Job)
    query = apply_job_filters(
        query,
        q=q,
        location=location,
        source=source,
        is_remote=is_remote,
        company=company,
    )
    return (
        query.order_by(Job.scraped_at.desc(), Job.posted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/sources", response_model=list[str])
def list_sources() -> list[str]:
    return available_sources()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/scrape", response_model=ScrapeResult)
def scrape_jobs(
    payload: ScrapeRequest | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ScrapeResult:
    """Trigger a scrape from external sources and store results (auth required)."""
    body = payload or ScrapeRequest()
    aggregator = JobAggregator()
    result = aggregator.scrape_and_store(
        db,
        query=body.query,
        sources=body.sources,
        limit_per_source=body.limit_per_source,
    )
    return ScrapeResult(**result)
