"""Email delivery service."""

from __future__ import annotations

import logging
from typing import Iterable

from app.config import settings
from app.models.job import Job
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailService:
    """Send transactional email via Brevo when configured; otherwise log."""

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

        if not settings.brevo_api_key:
            logger.info(
                "Email (dry-run) to=%s subject=%s\n%s",
                user.email,
                subject,
                body,
            )
            return True

        return self._send_via_brevo(to_email=user.email, subject=subject, text=body)

    def _send_via_brevo(self, to_email: str, subject: str, text: str) -> bool:
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException
        except ImportError:
            logger.error("sib-api-v3-sdk not installed; cannot send email")
            return False

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.brevo_api_key
        api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        payload = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": settings.email_from, "name": settings.email_from_name},
            subject=subject,
            text_content=text,
        )
        try:
            api.send_transac_email(payload)
            logger.info("Alert email sent to %s", to_email)
            return True
        except ApiException:
            logger.exception("Brevo API error sending to %s", to_email)
            return False
