"""Filtering utilities."""

from sqlalchemy.orm import Query

from app.models.job import Job


def apply_job_filters(
    query: Query,
    *,
    q: str | None = None,
    location: str | None = None,
    source: str | None = None,
    is_remote: bool | None = None,
    company: str | None = None,
    tags: str | None = None,
) -> Query:
    """Apply common search filters to a Job query."""
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Job.title.ilike(like))
            | (Job.description.ilike(like))
            | (Job.company.ilike(like))
            | (Job.tags.ilike(like))
        )
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if source:
        query = query.filter(Job.source == source.lower())
    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(is_remote))
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if tags:
        for tag in [t.strip() for t in tags.split(",") if t.strip()]:
            query = query.filter(Job.tags.ilike(f"%{tag}%"))
    return query


def job_matches_keywords(job: Job, keywords: str | None) -> bool:
    """Return True if job title/description/tags contain all comma-separated keywords."""
    if not keywords:
        return True
    haystack = " ".join(
        filter(
            None,
            [job.title or "", job.description or "", job.tags or "", job.company or ""],
        )
    ).lower()
    for kw in [k.strip().lower() for k in keywords.split(",") if k.strip()]:
        if kw not in haystack:
            return False
    return True
