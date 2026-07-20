"""Alert routes."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.schemas.job import JobOut
from app.services.auth_service import get_current_user
from app.services.email_service import EmailService
from app.utils.filters import apply_job_filters, job_matches_keywords

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/run")
def run_alerts_for_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Evaluate saved searches for the current user and email new matches."""
    searches = (
        db.query(SavedSearch)
        .filter(
            SavedSearch.user_id == current_user.id,
            SavedSearch.alerts_enabled.is_(True),
        )
        .all()
    )
    email = EmailService()
    summary: list[dict] = []

    for search in searches:
        matches = _find_matches(db, search)
        sent = email.send_job_alert(current_user, search.name, matches) if matches else False
        if matches:
            search.last_alerted_at = datetime.utcnow()
            db.add(search)
        summary.append(
            {
                "search_id": search.id,
                "name": search.name,
                "matches": len(matches),
                "emailed": sent,
            }
        )

    db.commit()
    return {"user_id": current_user.id, "results": summary}


@router.get("/preview/{search_id}", response_model=list[JobOut])
def preview_matches(
    search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Job]:
    search = (
        db.query(SavedSearch)
        .filter(SavedSearch.id == search_id, SavedSearch.user_id == current_user.id)
        .first()
    )
    if not search:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Saved search not found")
    return _find_matches(db, search, limit=50)


def _find_matches(db: Session, search: SavedSearch, limit: int = 25) -> list[Job]:
    query = db.query(Job)
    query = apply_job_filters(
        query,
        q=search.query,
        location=search.location,
        source=search.source,
        is_remote=search.is_remote,
    )
    if search.last_alerted_at:
        query = query.filter(Job.scraped_at > search.last_alerted_at)

    candidates = (
        query.order_by(Job.scraped_at.desc()).limit(limit * 3).all()
    )
    # Extra keyword filter on tags field
    matched = [j for j in candidates if job_matches_keywords(j, search.tags)]
    return matched[:limit]
