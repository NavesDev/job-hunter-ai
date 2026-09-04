from typing import Protocol

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.job import Job


class JobRepository(Protocol):
    """Persistence for collected jobs and application history."""

    def save_jobs(self, jobs: list[Job]) -> list[Job]:
        """Persist jobs, deduplicating by `Job.id`. Returns the persisted jobs."""
        ...

    def get_job(self, job_id: str) -> Job | None:
        """Return the job with this id, or None when it does not exist."""
        ...

    def save_application(self, result: ApplicationResult) -> None:
        """Record the outcome of an application attempt."""
        ...
