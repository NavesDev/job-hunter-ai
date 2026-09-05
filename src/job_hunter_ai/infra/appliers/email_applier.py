"""Applies to a job by email over SMTP."""

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.smtp_config import SmtpConfig
from job_hunter_ai.domain.errors import SmtpError
from job_hunter_ai.domain.time_utils import utc_now
from job_hunter_ai.infra.appliers.email_message import FALLBACK_TEMPLATE, build_message

REDACTED = "***"
SMTP_TIMEOUT_SECONDS = 30


class EmailApplier:
    """Sends the application email with the resume attached.

    Any transport failure becomes an `SmtpError` whose message is scrubbed of the
    SMTP username and password — a credential must never reach stderr, a log or
    the application history (see SECURITY.md).
    """

    name = "email"

    def __init__(self, smtp: SmtpConfig, fallback_template: Path = FALLBACK_TEMPLATE) -> None:
        self._smtp = smtp
        self._fallback_template = fallback_template

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        message = build_message(
            job,
            profile,
            recipient=options.get("email"),
            subject=options.get("subject"),
            sender=self._smtp.username,
            fallback_template=self._fallback_template,
        )
        self._send(message)
        return ApplicationResult(
            job_id=job.id,
            method=self.name,
            status=ApplicationStatus.SENT,
            applier=self.name,
            detail=f"sent to {message['To']}",
            applied_at=utc_now(),
        )

    def _send(self, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP(
                self._smtp.host, self._smtp.port, timeout=SMTP_TIMEOUT_SECONDS
            ) as server:
                if self._smtp.use_tls:
                    server.starttls()
                # A local development server (maildev, aiosmtpd) advertises no AUTH;
                # a real provider always does, and there the login is mandatory.
                if self._smtp.password and server.has_extn("auth"):
                    server.login(self._smtp.username, self._smtp.password)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise SmtpError(self._scrub(f"{type(exc).__name__}: {exc}")) from None

    def _scrub(self, text: str) -> str:
        """Remove the credentials from a message before it can reach the outside."""
        scrubbed = text
        for secret in (self._smtp.password, self._smtp.username):
            if secret:
                scrubbed = scrubbed.replace(secret, REDACTED)
        return scrubbed
