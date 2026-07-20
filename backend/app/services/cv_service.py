"""CV management service."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.cv import CV
from app.models.user import User
from app.schemas.cv import CVUpdate
from app.utils.cv_parser import cv_profile_text, extract_text_from_bytes, parse_cv_text

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def get_or_create_cv(db: Session, user: User) -> CV:
    cv = db.query(CV).filter(CV.user_id == user.id).first()
    if cv is None:
        cv = CV(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
        )
        db.add(cv)
        db.commit()
        db.refresh(cv)
    return cv


def update_cv(db: Session, user: User, payload: CVUpdate) -> CV:
    cv = get_or_create_cv(db, user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cv, key, value)
    # Re-parse for matching signals; do not wipe user-edited fields
    _apply_parse(cv, cv_profile_text(cv), fill_empty_profile_fields=False)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def upload_and_parse_cv(
    db: Session,
    user: User,
    file: UploadFile,
) -> CV:
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    try:
        text = extract_text_from_bytes(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    upload_dir = Path(getattr(settings, "upload_dir", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"user{user.id}_{uuid.uuid4().hex[:12]}{ext}"
    dest = upload_dir / safe_name
    dest.write_bytes(content)

    cv = get_or_create_cv(db, user)
    if cv.file_path and os.path.isfile(cv.file_path) and cv.file_path != str(dest):
        try:
            os.remove(cv.file_path)
        except OSError:
            pass

    cv.original_filename = filename
    cv.file_path = str(dest)
    cv.raw_text = text
    # On upload, fill empty profile fields from parse (titles, experience, etc.)
    _apply_parse(cv, text, prefer_extracted_contact=True, fill_empty_profile_fields=True)

    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def reparse_cv(db: Session, user: User) -> CV:
    cv = get_or_create_cv(db, user)
    # Prefer raw uploaded text for accuracy
    text = (cv.raw_text or "").strip() or cv_profile_text(cv)
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No CV content to parse. Upload a file or fill in your profile.",
        )
    _apply_parse(cv, text, prefer_extracted_contact=True, fill_empty_profile_fields=True)
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


def _apply_parse(
    cv: CV,
    text: str,
    prefer_extracted_contact: bool = False,
    fill_empty_profile_fields: bool = False,
) -> None:
    parsed = parse_cv_text(text)

    form_skills = [s.strip() for s in (cv.skills or "").split(",") if s.strip()]
    all_skills = list(dict.fromkeys(parsed.skills + form_skills))

    cv.parsed_skills = ",".join(all_skills) if all_skills else None
    cv.parsed_titles = ",".join(parsed.titles) if parsed.titles else None
    cv.parsed_keywords = ",".join(parsed.keywords) if parsed.keywords else None
    cv.parsed_at = datetime.utcnow()

    if prefer_extracted_contact or fill_empty_profile_fields:
        if parsed.email and not cv.email:
            cv.email = parsed.email
        if parsed.phone and not cv.phone:
            cv.phone = parsed.phone

    if fill_empty_profile_fields:
        if parsed.full_name and not cv.full_name:
            cv.full_name = parsed.full_name
        if parsed.suggested_headline and not cv.headline:
            cv.headline = parsed.suggested_headline
        if all_skills and not cv.skills:
            cv.skills = ", ".join(all_skills)
        if parsed.experience_text and not cv.experience:
            cv.experience = parsed.experience_text
        if parsed.education_text and not cv.education:
            cv.education = parsed.education_text
        if parsed.summary_text and not cv.summary:
            cv.summary = parsed.summary_text
