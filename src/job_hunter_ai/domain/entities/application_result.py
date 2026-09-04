from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApplicationStatus(StrEnum):
    """Possible outcomes of an application attempt. See docs/CONTRACT.md."""

    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class ApplicationResult:
    """The outcome of a single application attempt for a job."""

    job_id: str
    method: str
    status: ApplicationStatus
    applier: str
    detail: str = ""
    applied_at: datetime | None = None
