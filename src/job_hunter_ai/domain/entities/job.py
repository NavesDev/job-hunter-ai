from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Job:
    """A normalized job posting, independent of the platform it came from."""

    id: str
    source: str
    title: str
    company: str
    description: str = ""
    url: str | None = None
    apply_email: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    collected_at: datetime | None = None
