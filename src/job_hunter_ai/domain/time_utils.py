"""ISO 8601 UTC helpers. The single time representation of the whole project.

Every timestamp that crosses a boundary (database, CLI output) is a UTC string
ending in `Z`, as required by docs/CONTRACT.md.
"""

from datetime import UTC, datetime

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    """Current instant, always timezone-aware and in UTC."""
    return datetime.now(UTC)


def to_iso_utc(moment: datetime) -> str:
    """Serialize an instant as `2026-09-03T14:00:00Z`, converting to UTC when needed."""
    aware = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return aware.strftime(ISO_FORMAT)


def from_iso_utc(raw: str) -> datetime:
    """Parse an ISO 8601 UTC string back into an aware datetime."""
    return datetime.strptime(raw, ISO_FORMAT).replace(tzinfo=UTC)
