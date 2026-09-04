from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """The candidate's profile, built from the local non-sensitive configuration."""

    name: str
    contact_email: str
    resume_path: Path
    email_body_path: Path
    default_subject: str = ""
    # Generic fields reused by form appliers of any platform (phase 2).
    extra_fields: dict[str, str] = field(default_factory=dict)
