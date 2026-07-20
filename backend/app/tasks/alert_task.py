"""Alert email task."""

from datetime import datetime

from app.database import SessionLocal
from app.models.job import Job
from app.models.saved_search import SavedSearch
from app.models.user import User
from app.services.email_service import EmailService
from app.tasks.celery_app import celery_app
from app.utils.filters import apply_job_filters, job_matches_keywords


@celery_app.task(name="app.tasks.alert_task.process_alerts")
def process_alerts() -> dict:
    db = SessionLocal()
    email = EmailService()
    total_sent = 0
    try:
        searches = (
            db.query(SavedSearch)
            .filter(SavedSearch.alerts_enabled.is_(True))
            .all()
        )
        for search in searches:
            user = db.query(User).filter(User.id == search.user_id).first()
            if not user or not user.is_active:
                continue

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

            candidates = query.order_by(Job.scraped_at.desc()).limit(75).all()
            matches = [j for j in candidates if job_matches_keywords(j, search.tags)]
            if not matches:
                continue

            if email.send_job_alert(user, search.name, matches[:25]):
                search.last_alerted_at = datetime.utcnow()
                db.add(search)
                total_sent += 1

        db.commit()
        return {"sent": total_sent}
    finally:
        db.close()
