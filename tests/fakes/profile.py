"""Builds a `CandidateProfile` pointing at real temporary files."""

from pathlib import Path

from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile

RESUME_BYTES = b"%PDF-1.4 fake resume"
BODY_HTML = "<p>Hi {company} team, I am {name} applying for {title}. {contact_email}</p>"


def build_profile(tmp_path: Path, **overrides: object) -> CandidateProfile:
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(RESUME_BYTES)
    body = tmp_path / "email-body.html"
    body.write_text(BODY_HTML, encoding="utf-8")
    defaults: dict[str, object] = {
        "name": "Ada Lovelace",
        "contact_email": "ada@example.com",
        "resume_path": resume,
        "email_body_path": body,
        "default_subject": "Application - {title} - Ada Lovelace",
        "extra_fields": {},
    }
    return CandidateProfile(**{**defaults, **overrides})  # type: ignore[arg-type]
