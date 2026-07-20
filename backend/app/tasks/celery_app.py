"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "jobhunter",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scrape_task",
        "app.tasks.alert_task",
        "app.tasks.auto_apply_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scrape-jobs-every-6h": {
            "task": "app.tasks.scrape_task.scrape_all_jobs",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "send-alerts-hourly": {
            "task": "app.tasks.alert_task.process_alerts",
            "schedule": crontab(minute=15),
        },
        # Phase D: auto draft/send email applications twice daily
        "auto-apply-morning": {
            "task": "app.tasks.auto_apply_task.process_auto_apply",
            "schedule": crontab(minute=30, hour=8),
        },
        "auto-apply-evening": {
            "task": "app.tasks.auto_apply_task.process_auto_apply",
            "schedule": crontab(minute=30, hour=18),
        },
    },
)
