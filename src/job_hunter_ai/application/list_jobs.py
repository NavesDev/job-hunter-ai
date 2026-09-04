"""Use case: collect jobs from a source and persist them locally."""

from typing import Any

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.domain.ports.job_repository import JobRepository
from job_hunter_ai.domain.ports.job_source import JobSource

DEFAULT_MAX_LENGTH = 50


class ListJobsUseCase:
    """Fetches from a `JobSource` and stores through a `JobRepository`.

    Both ports arrive by constructor injection: the use case never knows which
    platform or which database is behind them (docs/CODE_STANDARDS.md).
    """

    def __init__(self, source: JobSource, repository: JobRepository) -> None:
        self._source = source
        self._repository = repository

    def execute(self, max_length: int = DEFAULT_MAX_LENGTH, **options: Any) -> list[Job]:
        """Return the persisted jobs, deduplicated by id and capped at `max_length`."""
        if max_length < 1:
            raise InvalidInputError("--max-length must be a positive integer")
        jobs = self._source.fetch(max_length=max_length, **options)
        return self._repository.save_jobs(jobs[:max_length])
