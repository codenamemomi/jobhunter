"""Rule-based job matching against a parsed CV (Phase 1 — no AI)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.cv import CV
from app.models.job import Job
from app.utils.cv_parser import parse_cv_text, cv_profile_text


@dataclass
class MatchResult:
    job: Job
    score: float  # 0–100
    matched_skills: list[str]
    matched_titles: list[str]
    reasons: list[str]


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def ensure_cv_parsed(cv: CV) -> tuple[list[str], list[str], list[str]]:
    """Return skills/titles/keywords, re-parsing from profile text if needed."""
    skills = split_csv(cv.parsed_skills)
    titles = split_csv(cv.parsed_titles)
    keywords = split_csv(cv.parsed_keywords)

    if skills or titles:
        return skills, titles, keywords

    # Fall back: parse structured fields + raw text
    text = cv_profile_text(cv)
    if not text.strip():
        return [], [], []

    parsed = parse_cv_text(text)
    # also merge explicit skills field tokens
    for token in split_csv(cv.skills):
        if token not in parsed.skills:
            parsed.skills.append(token)
    return parsed.skills, parsed.titles, parsed.keywords


def score_job(
    job: Job,
    skills: list[str],
    titles: list[str],
    keywords: list[str],
    prefer_remote: bool | None = None,
) -> MatchResult:
    haystack = " ".join(
        filter(
            None,
            [
                job.title or "",
                job.company or "",
                job.location or "",
                job.description or "",
                job.tags or "",
            ],
        )
    ).lower()

    matched_skills: list[str] = []
    for skill in skills:
        if skill.lower() in haystack:
            matched_skills.append(skill)

    matched_titles: list[str] = []
    for title in titles:
        # loose: all significant words present
        words = [w for w in title.lower().split() if len(w) > 2]
        if words and all(w in haystack for w in words):
            matched_titles.append(title)
        elif title.lower() in haystack:
            matched_titles.append(title)

    matched_keywords = [k for k in keywords if k.lower() in haystack]

    # Scoring weights (out of 100)
    skill_score = 0.0
    if skills:
        skill_score = (len(matched_skills) / len(skills)) * 60.0
    elif matched_keywords:
        skill_score = min(20.0, len(matched_keywords) * 5.0)

    title_score = 0.0
    if titles:
        title_score = (len(matched_titles) / len(titles)) * 25.0
    elif any(t in (job.title or "").lower() for t in ("engineer", "developer", "data", "manager")):
        title_score = 5.0

    keyword_score = min(10.0, len(matched_keywords) * 2.5)

    remote_score = 0.0
    if prefer_remote is True and job.is_remote:
        remote_score = 5.0
    elif prefer_remote is False and not job.is_remote:
        remote_score = 3.0

    score = min(100.0, skill_score + title_score + keyword_score + remote_score)

    reasons: list[str] = []
    if matched_skills:
        reasons.append(f"Skills: {', '.join(matched_skills[:8])}")
    if matched_titles:
        reasons.append(f"Title fit: {', '.join(matched_titles[:3])}")
    if matched_keywords:
        reasons.append(f"Keywords: {', '.join(matched_keywords[:5])}")
    if remote_score and job.is_remote:
        reasons.append("Remote role")
    if not reasons:
        reasons.append("Low overlap with your profile")

    return MatchResult(
        job=job,
        score=round(score, 1),
        matched_skills=matched_skills,
        matched_titles=matched_titles,
        reasons=reasons,
    )


def match_jobs_for_cv(
    db: Session,
    cv: CV,
    *,
    limit: int = 25,
    min_score: float = 5.0,
    prefer_remote: bool | None = None,
    email_apply_only: bool = False,
) -> tuple[list[MatchResult], list[str], list[str]]:
    skills, titles, keywords = ensure_cv_parsed(cv)
    if not skills and not titles and not keywords and not (cv.skills or "").strip():
        return [], skills, titles

    q = db.query(Job).order_by(Job.scraped_at.desc())
    if email_apply_only:
        q = q.filter(Job.apply_method == "email", Job.apply_email.isnot(None))
    jobs = q.limit(500).all()

    results: list[MatchResult] = []
    for job in jobs:
        result = score_job(job, skills, titles, keywords, prefer_remote=prefer_remote)
        if result.score >= min_score:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit], skills, titles
