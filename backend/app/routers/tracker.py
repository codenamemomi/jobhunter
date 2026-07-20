"""Tracker routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.job import Job
from app.models.tracker import APPLICATION_STATUSES, Application
from app.models.user import User
from app.schemas.tracker import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Application]:
    q = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.user_id == current_user.id)
    )
    if status:
        q = q.filter(Application.status == status)
    return q.order_by(Application.updated_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {list(APPLICATION_STATUSES)}",
        )
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = (
        db.query(Application)
        .filter(
            Application.user_id == current_user.id,
            Application.job_id == payload.job_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already tracking this job")

    app = Application(
        user_id=current_user.id,
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
        applied_at=datetime.utcnow() if payload.status == "applied" else None,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    # reload with job
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == app.id)
        .one()
    )


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Application:
    app = _owned_application(db, current_user.id, application_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        if data["status"] not in APPLICATION_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"status must be one of {list(APPLICATION_STATUSES)}",
            )
        if data["status"] == "applied" and app.applied_at is None:
            app.applied_at = datetime.utcnow()
        app.status = data["status"]
    if "notes" in data:
        app.notes = data["notes"]
    app.updated_at = datetime.utcnow()
    db.add(app)
    db.commit()
    return (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.id == app.id)
        .one()
    )


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    app = _owned_application(db, current_user.id, application_id)
    db.delete(app)
    db.commit()


@router.get("/statuses", response_model=list[str])
def list_statuses() -> list[str]:
    return list(APPLICATION_STATUSES)


def _owned_application(db: Session, user_id: int, application_id: int) -> Application:
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == user_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app
