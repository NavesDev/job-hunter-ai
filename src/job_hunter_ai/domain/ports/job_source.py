from typing import Any, Protocol

from job_hunter_ai.domain.entities.job import Job


class JobSource(Protocol):
    """A source of jobs. One implementation per platform, resolved by a registry."""

    name: str

    def fetch(self, max_length: int, **options: Any) -> list[Job]:
        """Return normalized jobs from the source, at most `max_length` of them."""
        ...
