from typing import Any, Protocol

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job


class JobApplier(Protocol):
    """A way of applying to a job (email, a given platform's form)."""

    name: str

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        """Apply to the job and return the outcome. Never raises a business exception."""
        ...
