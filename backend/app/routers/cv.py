"""CV routes."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.cv import CVOut, CVUpdate, JobMatchOut, MatchResponse
from app.schemas.job import JobOut
from app.services.auth_service import get_current_user
from app.services.cv_service import (
    get_or_create_cv,
    reparse_cv,
    update_cv,
    upload_and_parse_cv,
)
from app.services.match_service import match_jobs_for_cv
from app.utils.pdf_generator import cv_to_html, generate_cv_pdf

router = APIRouter(prefix="/cv", tags=["cv"])


@router.get("", response_model=CVOut)
def get_cv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CVOut:
    return CVOut.from_model(get_or_create_cv(db, current_user))


@router.put("", response_model=CVOut)
def put_cv(
    payload: CVUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CVOut:
    return CVOut.from_model(update_cv(db, current_user, payload))


@router.post("/upload", response_model=CVOut)
async def upload_cv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CVOut:
    """Upload PDF/DOCX/TXT, extract text, parse skills (rule-based)."""
    cv = upload_and_parse_cv(db, current_user, file)
    return CVOut.from_model(cv)


@router.post("/parse", response_model=CVOut)
def parse_cv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CVOut:
    """Re-run rule-based parse on stored CV text + profile fields."""
    return CVOut.from_model(reparse_cv(db, current_user))


@router.get("/matches", response_model=MatchResponse)
def cv_job_matches(
    limit: int = 25,
    min_score: float = 5.0,
    prefer_remote: bool | None = None,
    email_apply_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MatchResponse:
    """Score jobs against the current user's parsed CV (no AI)."""
    cv = get_or_create_cv(db, current_user)
    matches, skills, titles = match_jobs_for_cv(
        db,
        cv,
        limit=min(max(limit, 1), 100),
        min_score=min_score,
        prefer_remote=prefer_remote,
        email_apply_only=email_apply_only,
    )
    if not skills and not titles and not (cv.skills or cv.raw_text):
        raise HTTPException(
            status_code=400,
            detail="No skills found yet. Upload a CV or add skills to your profile, then parse.",
        )
    return MatchResponse(
        profile_skills=skills,
        profile_titles=titles,
        matches=[
            JobMatchOut(
                job=JobOut.model_validate(m.job),
                score=m.score,
                matched_skills=m.matched_skills,
                matched_titles=m.matched_titles,
                reasons=m.reasons,
            )
            for m in matches
        ],
    )


@router.get("/html", response_class=HTMLResponse)
def cv_html(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HTMLResponse:
    cv = get_or_create_cv(db, current_user)
    return HTMLResponse(content=cv_to_html(cv))


@router.get("/pdf")
def cv_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    cv = get_or_create_cv(db, current_user)
    try:
        pdf_bytes = generate_cv_pdf(cv)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    filename = f"{(cv.full_name or 'cv').replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
