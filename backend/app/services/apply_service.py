"""Draft and send email applications with CV attachment."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.cv import CV
from app.models.job import Job
from app.models.tracker import Application
from app.models.user import User
from app.services.cv_service import get_or_create_cv
from app.services.email_service import EmailService
from app.services.match_service import match_jobs_for_cv
from app.utils.pdf_generator import generate_cv_pdf

logger = logging.getLogger(__name__)


def build_application_email(user: User, job: Job, cv=None) -> tuple[str, str, str]:
    """Return (to, subject, body) for an email application."""
    if not job.apply_email:
        raise HTTPException(
            status_code=400,
            detail="This job has no application email. Open the listing URL instead.",
        )

    name = user.full_name or (cv.full_name if cv else None) or user.email
    headline = (cv.headline if cv else None) or "software professional"
    skills = ""
    if cv and cv.parsed_skills:
        skills = ", ".join(cv.parsed_skills.split(",")[:8])
    elif cv and cv.skills:
        skills = cv.skills

    company = job.company or "your team"
    subject = f"Application: {job.title} — {name}"

    body_lines = [
        f"Hello {company} hiring team,",
        "",
        f"I'm writing to apply for the {job.title} role"
        + (f" at {job.company}" if job.company else "")
        + ".",
        "",
        f"I'm {name}, a {headline}.",
    ]
    if skills:
        body_lines.append(f"Key skills: {skills}.")
    body_lines.extend(
        [
            "",
            "Please find my CV attached. I'd welcome the chance to discuss how I can contribute.",
            "",
            "Best regards,",
            name,
            user.email,
        ]
    )
    # Intentionally no job listing URL — keep the message clean

    return job.apply_email, subject, "\n".join(body_lines)


def resolve_cv_attachment(cv: CV, user: User) -> tuple[bytes | None, str | None]:
    """
    Prefer the user's uploaded CV file (PDF/DOCX/etc).
    Fall back to a generated PDF only if nothing was uploaded.
    """
    if cv.file_path and os.path.isfile(cv.file_path):
        try:
            data = Path(cv.file_path).read_bytes()
            name = cv.original_filename or Path(cv.file_path).name
            if data:
                return data, name
        except OSError as exc:
            logger.warning("Could not read uploaded CV %s: %s", cv.file_path, exc)

    # No upload — last resort generated profile PDF
    try:
        pdf = generate_cv_pdf(cv)
        fname = f"{(cv.full_name or user.full_name or 'CV').replace(' ', '_')}.pdf"
        return pdf, fname
    except RuntimeError as exc:
        logger.warning("Generated CV PDF unavailable: %s", exc)
        return None, None


def get_or_create_application(db: Session, user: User, job_id: int) -> Application:
    app = (
        db.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job_id)
        .first()
    )
    if app:
        return app
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    app = Application(user_id=user.id, job_id=job_id, status="wishlist")
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def create_draft(
    db: Session,
    user: User,
    job_id: int,
    *,
    subject: str | None = None,
    body: str | None = None,
    match_score: float | None = None,
    is_auto: bool = False,
) -> Application:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.apply_method != "email" or not job.apply_email:
        raise HTTPException(
            status_code=400,
            detail="Only email-apply jobs can be drafted for auto/email send.",
        )

    cv = get_or_create_cv(db, user)
    to, default_subject, default_body = build_application_email(user, job, cv)

    app = (
        db.query(Application)
        .filter(Application.user_id == user.id, Application.job_id == job_id)
        .first()
    )
    if app and app.status == "applied" and app.sent_at:
        raise HTTPException(status_code=400, detail="Already applied to this job")

    if not app:
        app = Application(user_id=user.id, job_id=job_id)

    app.status = "draft"
    app.apply_channel = "email"
    app.email_to = to
    app.email_subject = subject or default_subject
    app.email_body = body or default_body
    app.match_score = match_score
    app.is_auto = is_auto
    app.send_error = None
    app.updated_at = datetime.utcnow()

    db.add(app)
    db.commit()
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == app.id)
        .one()
    )


def update_draft(
    db: Session,
    user: User,
    application_id: int,
    *,
    subject: str | None = None,
    body: str | None = None,
    notes: str | None = None,
) -> Application:
    app = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == application_id, Application.user_id == user.id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status not in ("draft", "wishlist"):
        raise HTTPException(status_code=400, detail="Only drafts can be edited this way")
    if subject is not None:
        app.email_subject = subject
    if body is not None:
        app.email_body = body
    if notes is not None:
        app.notes = notes
    if app.status == "wishlist" and app.email_to:
        app.status = "draft"
    app.updated_at = datetime.utcnow()
    db.add(app)
    db.commit()
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == app.id)
        .one()
    )


def send_application(
    db: Session,
    user: User,
    application_id: int,
    *,
    attach_cv: bool = True,
) -> Application:
    app = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == application_id, Application.user_id == user.id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status == "applied" and app.sent_at:
        raise HTTPException(status_code=400, detail="Already sent")

    job = app.job
    if not job:
        raise HTTPException(status_code=404, detail="Job missing")

    cv = get_or_create_cv(db, user)
    if not app.email_to or not app.email_subject or not app.email_body:
        to, subject, body = build_application_email(user, job, cv)
        app.email_to = app.email_to or to
        app.email_subject = app.email_subject or subject
        app.email_body = app.email_body or body

    if not app.email_to:
        raise HTTPException(status_code=400, detail="No recipient email")

    attachment_bytes = None
    attachment_name = None
    if attach_cv:
        attachment_bytes, attachment_name = resolve_cv_attachment(cv, user)
        if not attachment_bytes:
            logger.warning("No CV file to attach for user %s", user.id)

    email = EmailService()
    try:
        provider = email.send(
            to_email=app.email_to,
            subject=app.email_subject,
            text=app.email_body,
            reply_to=user.email,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
        )
    except Exception as exc:  # EmailSendError or unexpected
        from app.services.email_service import EmailSendError

        detail = str(exc)
        if not isinstance(exc, EmailSendError):
            logger.exception("Unexpected email failure")
            detail = f"Email send failed: {exc}"
        app.send_error = detail
        db.add(app)
        db.commit()
        raise HTTPException(status_code=502, detail=detail) from exc

    app.status = "applied"
    app.applied_at = datetime.utcnow()
    app.sent_at = datetime.utcnow()
    app.apply_channel = "email"
    app.send_error = None
    app.updated_at = datetime.utcnow()
    note_line = (
        f"Email application sent via {provider} to {app.email_to} "
        f"at {app.sent_at.isoformat()}Z"
    )
    if provider == "dry_run":
        note_line += " (DRY-RUN — no real email delivered; configure SMTP or Brevo)"
    app.notes = f"{app.notes}\n{note_line}".strip() if app.notes else note_line
    db.add(app)
    db.commit()
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == app.id)
        .one()
    )


def list_queue(
    db: Session,
    user: User,
    status: str | None = "draft",
) -> list[Application]:
    q = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.user_id == user.id)
    )
    if status:
        q = q.filter(Application.status == status)
    return q.order_by(Application.updated_at.desc()).all()


def count_sent_today(db: Session, user_id: int) -> int:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(Application)
        .filter(
            Application.user_id == user_id,
            Application.sent_at.isnot(None),
            Application.sent_at >= start,
        )
        .count()
    )


def auto_process_user(db: Session, user: User) -> dict:
    """
    Phase D: create drafts for high-scoring email-apply jobs.
    Optionally send if auto_send_enabled and under daily limit.
    """
    result = {"drafted": 0, "sent": 0, "skipped": 0, "errors": []}
    if not user.auto_draft_enabled and not user.auto_send_enabled:
        return result

    cv = get_or_create_cv(db, user)
    prefer_remote = user.auto_prefer_remote if user.auto_prefer_remote is not None else True
    matches, skills, _titles = match_jobs_for_cv(
        db,
        cv,
        limit=50,
        min_score=float(user.auto_min_score or 75),
        prefer_remote=prefer_remote if prefer_remote else None,
    )
    if not skills and not (cv.skills or cv.raw_text):
        result["errors"].append("No CV skills — upload/parse CV first")
        return result

    sent_today = count_sent_today(db, user.id)
    daily_limit = int(user.auto_daily_limit or 5)

    for m in matches:
        job = m.job
        if user.auto_email_only and (job.apply_method != "email" or not job.apply_email):
            result["skipped"] += 1
            continue

        existing = (
            db.query(Application)
            .filter(Application.user_id == user.id, Application.job_id == job.id)
            .first()
        )
        if existing and existing.status in ("applied", "rejected", "withdrawn"):
            result["skipped"] += 1
            continue
        if existing and existing.status == "draft" and not user.auto_send_enabled:
            result["skipped"] += 1
            continue

        try:
            if not existing or existing.status in ("wishlist", "draft"):
                if not existing or existing.status != "draft":
                    app = create_draft(
                        db,
                        user,
                        job.id,
                        match_score=m.score,
                        is_auto=True,
                    )
                    result["drafted"] += 1
                else:
                    app = existing

                if user.auto_send_enabled and sent_today < daily_limit:
                    if app.status == "draft":
                        send_application(db, user, app.id, attach_cv=True)
                        sent_today += 1
                        result["sent"] += 1
        except HTTPException as exc:
            result["errors"].append(f"job {job.id}: {exc.detail}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("auto_process job %s", job.id)
            result["errors"].append(f"job {job.id}: {exc}")

    return result


def auto_process_all_users(db: Session) -> dict:
    users = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            (User.auto_draft_enabled.is_(True)) | (User.auto_send_enabled.is_(True)),
        )
        .all()
    )
    summary = {"users": 0, "drafted": 0, "sent": 0}
    for user in users:
        r = auto_process_user(db, user)
        summary["users"] += 1
        summary["drafted"] += r["drafted"]
        summary["sent"] += r["sent"]
    return summary
