"""The outcome of making sure a platform session exists."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SessionStatus(StrEnum):
    """What the `login-platform` command had to do. See docs/CONTRACT.md."""

    AUTHENTICATED = "authenticated"
    ALREADY_AUTHENTICATED = "already_authenticated"


@dataclass(frozen=True, slots=True)
class SessionResult:
    """A usable session for one platform, and where the browser profile holding it lives."""

    source: str
    status: SessionStatus
    profile_dir: str
    detail: str = ""
    checked_at: datetime | None = None
