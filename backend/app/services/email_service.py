"""Email delivery: Gmail/SMTP app password, Brevo API, or dry-run."""

from __future__ import annotations

import base64
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Iterable

from app.config import settings
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when a real provider is configured but send fails."""

    def __init__(self, message: str, provider: str | None = None):
        super().__init__(message)
        self.provider = provider
        self.message = message


class EmailService:
    """Send mail via SMTP (Gmail app password) or Brevo; dry-run if neither configured."""

    def provider_name(self) -> str:
        return settings.resolved_email_provider

    def send_job_alert(self, user: User, search_name: str, jobs: Iterable[Job]) -> bool:
        jobs_list = list(jobs)
        if not jobs_list:
            return False

        subject = f"JobHunter: {len(jobs_list)} new match(es) for “{search_name}”"
        lines = [
            f"Hi {user.full_name or user.email},",
            "",
            f"New jobs matching your saved search “{search_name}”:",
            "",
        ]
        for job in jobs_list[:25]:
            lines.append(f"• {job.title} @ {job.company or 'Unknown'} ({job.source})")
            if job.url:
                lines.append(f"  {job.url}")
            lines.append("")
        lines.append("— JobHunter")
        body = "\n".join(lines)

        self.send(
            to_email=user.email,
            subject=subject,
            text=body,
            reply_to=None,
        )
        return True

    def send_application_email(
        self,
        *,
        to_email: str,
        subject: str,
        text: str,
        reply_to: str | None = None,
        attachment_bytes: bytes | None = None,
        attachment_name: str | None = None,
    ) -> bool:
        self.send(
            to_email=to_email,
            subject=subject,
            text=text,
            reply_to=reply_to,
            attachment_bytes=attachment_bytes,
            attachment_name=attachment_name,
        )
        return True

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        text: str,
        reply_to: str | None = None,
        attachment_bytes: bytes | None = None,
        attachment_name: str | None = None,
    ) -> str:
        """
        Send email. Returns provider used: smtp | brevo | dry_run.
        Raises EmailSendError on hard failures for real providers.
        """
        provider = settings.resolved_email_provider
        logger.info(
            "Email send via=%s to=%s from=%s subject=%s",
            provider,
            to_email,
            settings.email_from,
            subject,
        )

        if provider == "dry_run":
            logger.info(
                "Application email (dry-run) to=%s reply_to=%s attachment=%s\n%s",
                to_email,
                reply_to,
                attachment_name or "none",
                text,
            )
            return "dry_run"

        if provider == "smtp":
            self._send_via_smtp(
                to_email=to_email,
                subject=subject,
                text=text,
                reply_to=reply_to,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
            )
            return "smtp"

        if provider == "brevo":
            self._send_via_brevo(
                to_email=to_email,
                subject=subject,
                text=text,
                reply_to=reply_to,
                attachment_bytes=attachment_bytes,
                attachment_name=attachment_name,
            )
            return "brevo"

        raise EmailSendError(f"Unknown email provider: {provider}", provider=provider)

    def _send_via_smtp(
        self,
        *,
        to_email: str,
        subject: str,
        text: str,
        reply_to: str | None,
        attachment_bytes: bytes | None,
        attachment_name: str | None,
    ) -> None:
        user = (settings.smtp_user or settings.email_from or "").strip()
        password = (settings.smtp_password or "").replace(" ", "")  # Gmail app pw often has spaces
        from_addr = (settings.email_from or user).strip()

        if not user or not password:
            raise EmailSendError(
                "SMTP not configured. Set SMTP_USER and SMTP_PASSWORD (Gmail app password).",
                provider="smtp",
            )
        if not from_addr:
            raise EmailSendError("EMAIL_FROM is empty.", provider="smtp")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{settings.email_from_name} <{from_addr}>" if settings.email_from_name else from_addr
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(text)

        if attachment_bytes and attachment_name:
            maintype, subtype = "application", "octet-stream"
            lower = attachment_name.lower()
            if lower.endswith(".pdf"):
                maintype, subtype = "application", "pdf"
            elif lower.endswith(".docx"):
                maintype, subtype = (
                    "application",
                    "vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            elif lower.endswith(".doc"):
                maintype, subtype = "application", "msword"
            elif lower.endswith(".txt"):
                maintype, subtype = "text", "plain"
            msg.add_attachment(
                attachment_bytes,
                maintype=maintype,
                subtype=subtype,
                filename=attachment_name,
            )

        try:
            if settings.smtp_use_tls:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(user, password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                    server.login(user, password)
                    server.send_message(msg)
        except smtplib.SMTPAuthenticationError as exc:
            raise EmailSendError(
                "Gmail/SMTP login failed. Use an App Password (not your normal Gmail password), "
                "with 2-Step Verification enabled. "
                f"Detail: {exc.smtp_error.decode() if isinstance(exc.smtp_error, bytes) else exc.smtp_error}",
                provider="smtp",
            ) from exc
        except smtplib.SMTPException as exc:
            raise EmailSendError(f"SMTP error: {exc}", provider="smtp") from exc
        except OSError as exc:
            raise EmailSendError(f"SMTP connection error: {exc}", provider="smtp") from exc

        logger.info("SMTP email sent to %s subject=%s", to_email, subject)

    def _send_via_brevo(
        self,
        *,
        to_email: str,
        subject: str,
        text: str,
        reply_to: str | None,
        attachment_bytes: bytes | None,
        attachment_name: str | None,
    ) -> None:
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except ImportError as exc:
            raise EmailSendError(
                "sib-api-v3-sdk not installed. pip install sib-api-v3-sdk",
                provider="brevo",
            ) from exc

        if not settings.brevo_api_key:
            raise EmailSendError("BREVO_API_KEY is empty.", provider="brevo")

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.brevo_api_key
        api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        kwargs: dict = {
            "to": [{"email": to_email}],
            "sender": {"email": settings.email_from, "name": settings.email_from_name or "JobHunter"},
            "subject": subject,
            "text_content": text,
        }
        if reply_to:
            kwargs["reply_to"] = {"email": reply_to}
        if attachment_bytes and attachment_name:
            kwargs["attachment"] = [
                {
                    "content": base64.b64encode(attachment_bytes).decode("ascii"),
                    "name": attachment_name,
                }
            ]

        payload = sib_api_v3_sdk.SendSmtpEmail(**kwargs)
        try:
            api.send_transac_email(payload)
            logger.info("Brevo email sent to %s subject=%s", to_email, subject)
        except ApiException as exc:
            body = getattr(exc, "body", None) or str(exc)
            hint = (
                " Brevo requires EMAIL_FROM to be a verified sender in the Brevo dashboard "
                "(Senders → Add a sender). Free accounts cannot freely send as any Gmail address "
                "until that address is verified. Prefer SMTP + Gmail app password for Gmail."
            )
            raise EmailSendError(
                f"Brevo API error ({exc.status}): {body}.{hint}",
                provider="brevo",
            ) from exc
