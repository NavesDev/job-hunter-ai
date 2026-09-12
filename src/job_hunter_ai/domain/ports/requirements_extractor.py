from typing import Protocol

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.job_requirements import JobRequirements


class RequirementsExtractor(Protocol):
    """Reads the requirements out of a job, in whatever shape its platform publishes them."""

    name: str

    def extract(self, job: Job) -> JobRequirements: ...
