"""Email-apply draft / send / queue / auto-settings routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import reload_settings, settings
from app.database import get_db
from app.models.user import User
from app.schemas.tracker import (
    ApplicationOut,
    AutoSettingsOut,
    AutoSettingsUpdate,
    DraftCreate,
    DraftUpdate,
    SendRequest,
)
from app.services.apply_service import (
    auto_process_user,
    count_sent_today,
    create_draft,
    list_queue,
    send_application,
    update_draft,
)
from app.services.auth_service import get_current_user
from app.services.email_service import EmailSendError, EmailService

router = APIRouter(prefix="/apply", tags=["apply"])


class EmailStatusOut(BaseModel):
    provider: str
    email_from: str
    email_from_name: str
    smtp_host: str
    smtp_user_set: bool
    smtp_password_set: bool
    brevo_key_set: bool
    hint: str


class TestEmailRequest(BaseModel):
    to_email: EmailStr | None = Field(
        default=None,
        description="Defaults to your account email",
    )


class TestEmailResponse(BaseModel):
    ok: bool
    provider: str
    detail: str


@router.get("/queue", response_model=list[ApplicationOut])
def get_queue(
    status: str | None = Query("draft", description="draft | applied | wishlist | empty for all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApplicationOut]:
    st = status if status not in ("", "all") else None
    return list_queue(db, current_user, status=st)


@router.post("/draft", response_model=ApplicationOut, status_code=201)
def draft_application(
    payload: DraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    return create_draft(
        db,
        current_user,
        payload.job_id,
        subject=payload.subject,
        body=payload.body,
        match_score=payload.match_score,
    )


@router.patch("/draft/{application_id}", response_model=ApplicationOut)
def patch_draft(
    application_id: int,
    payload: DraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    return update_draft(
        db,
        current_user,
        application_id,
        subject=payload.subject,
        body=payload.body,
        notes=payload.notes,
    )


@router.post("/send/{application_id}", response_model=ApplicationOut)
def send_draft(
    application_id: int,
    payload: SendRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicationOut:
    body = payload or SendRequest()
    return send_application(db, current_user, application_id, attach_cv=body.attach_cv)


@router.get("/settings", response_model=AutoSettingsOut)
def get_auto_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutoSettingsOut:
    return AutoSettingsOut(
        auto_draft_enabled=bool(current_user.auto_draft_enabled),
        auto_send_enabled=bool(current_user.auto_send_enabled),
        auto_min_score=float(current_user.auto_min_score or 75),
        auto_daily_limit=int(current_user.auto_daily_limit or 5),
        auto_prefer_remote=bool(current_user.auto_prefer_remote)
        if current_user.auto_prefer_remote is not None
        else True,
        auto_email_only=bool(current_user.auto_email_only)
        if current_user.auto_email_only is not None
        else True,
        sent_today=count_sent_today(db, current_user.id),
    )


@router.put("/settings", response_model=AutoSettingsOut)
def put_auto_settings(
    payload: AutoSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutoSettingsOut:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)
    # Safety: auto-send implies drafts
    if current_user.auto_send_enabled:
        current_user.auto_draft_enabled = True
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return get_auto_settings(db=db, current_user=current_user)


@router.post("/auto-run")
def run_auto_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually trigger Phase D auto-draft / auto-send for current user."""
    return auto_process_user(db, current_user)


@router.get("/email-status", response_model=EmailStatusOut)
def email_status(_: User = Depends(get_current_user)) -> EmailStatusOut:
    """Show which mail provider is active (no secrets)."""
    reload_settings()
    provider = settings.resolved_email_provider
    if provider == "dry_run":
        hint = (
            "No real mailer configured. For Gmail: set EMAIL_PROVIDER=smtp, "
            "SMTP_USER, SMTP_PASSWORD (app password), EMAIL_FROM. "
            "For Brevo: set BREVO_API_KEY and verify EMAIL_FROM as a sender."
        )
    elif provider == "brevo":
        hint = (
            "Using Brevo. EMAIL_FROM must be a verified sender in Brevo dashboard. "
            "If send fails with 400, verify the sender or switch to Gmail SMTP."
        )
    else:
        hint = "Using SMTP (e.g. Gmail app password). EMAIL_FROM should match SMTP_USER for Gmail."
    return EmailStatusOut(
        provider=provider,
        email_from=settings.email_from,
        email_from_name=settings.email_from_name,
        smtp_host=settings.smtp_host,
        smtp_user_set=bool(settings.smtp_user or settings.email_from),
        smtp_password_set=bool(settings.smtp_password),
        brevo_key_set=bool(settings.brevo_api_key),
        hint=hint,
    )


@router.post("/test-email", response_model=TestEmailResponse)
def test_email(
    payload: TestEmailRequest | None = None,
    current_user: User = Depends(get_current_user),
) -> TestEmailResponse:
    """Send a short test message so you can verify SMTP/Brevo works."""
    reload_settings()
    to = (payload.to_email if payload and payload.to_email else None) or current_user.email
    try:
        provider = EmailService().send(
            to_email=to,
            subject="JobHunter test email",
            text=(
                f"Hi {current_user.full_name or current_user.email},\n\n"
                "This is a test message from JobHunter.\n"
                f"Provider: {settings.resolved_email_provider}\n"
                f"From: {settings.email_from}\n\n"
                "If you received this, outbound email is working.\n"
            ),
            reply_to=current_user.email,
        )
        if provider == "dry_run":
            return TestEmailResponse(
                ok=False,
                provider=provider,
                detail=(
                    "DRY-RUN only — nothing was delivered. Configure Gmail app password "
                    "(SMTP_PASSWORD) or a working BREVO_API_KEY, then restart the API."
                ),
            )
        return TestEmailResponse(
            ok=True,
            provider=provider,
            detail=f"Test email accepted by {provider} for {to}. Check inbox/spam.",
        )
    except EmailSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
