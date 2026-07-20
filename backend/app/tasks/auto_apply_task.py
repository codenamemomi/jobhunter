"""Scheduled auto-draft / auto-send for email applications."""

from app.database import SessionLocal
from app.services.apply_service import auto_process_all_users
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.auto_apply_task.process_auto_apply")
def process_auto_apply() -> dict:
    db = SessionLocal()
    try:
        return auto_process_all_users(db)
    finally:
        db.close()
