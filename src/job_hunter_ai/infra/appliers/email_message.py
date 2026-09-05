"""Builds the application email: recipient, subject, HTML body and resume attachment.

Separated from the transport so the message can be asserted without a server, and
so a change in the template rules never touches the SMTP code.
"""

from email.message import EmailMessage
from pathlib import Path

from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import InvalidInputError

FALLBACK_TEMPLATE = Path("config/templates/email-body.example.html")
RESUME_MIME = ("application", "pdf")


def build_message(
    job: Job,
    profile: CandidateProfile,
    *,
    recipient: str | None = None,
    subject: str | None = None,
    sender: str | None = None,
    fallback_template: Path = FALLBACK_TEMPLATE,
) -> EmailMessage:
    """Assemble the application email, failing fast on anything missing."""
    message = EmailMessage()
    message["To"] = resolve_recipient(job, recipient)
    message["From"] = sender or profile.contact_email or profile.name
    message["Subject"] = render(subject or profile.default_subject, job, profile)
    message.set_content(
        "This application is an HTML message; please read it in an HTML-capable client."
    )
    message.add_alternative(render(_read_body(profile, fallback_template), job, profile), "html")
    _attach_resume(message, profile.resume_path)
    return message


def resolve_recipient(job: Job, recipient: str | None) -> str:
    """`--email` wins over the job's own address; with neither, the input is invalid."""
    address = recipient or job.apply_email
    if not address or not address.strip():
        raise InvalidInputError(
            f"no recipient for job {job.id}: pass --email or give the job an apply_email"
        )
    return address.strip()


def render(template: str, job: Job, profile: CandidateProfile) -> str:
    """Replace the documented placeholders, leaving an unknown one untouched."""
    values = {
        "name": profile.name,
        "contact_email": profile.contact_email,
        "title": job.title,
        "company": job.company,
    }
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _read_body(profile: CandidateProfile, fallback_template: Path) -> str:
    if profile.email_body_path.is_file():
        return profile.email_body_path.read_text(encoding="utf-8")
    if fallback_template.is_file():
        return fallback_template.read_text(encoding="utf-8")
    raise InvalidInputError(
        f"no email body: neither {profile.email_body_path} nor {fallback_template} exists"
    )


def _attach_resume(message: EmailMessage, resume_path: Path) -> None:
    if not resume_path.is_file():
        raise InvalidInputError(f"resume not found: {resume_path}")
    message.add_attachment(
        resume_path.read_bytes(),
        maintype=RESUME_MIME[0],
        subtype=RESUME_MIME[1],
        filename=resume_path.name,
    )
