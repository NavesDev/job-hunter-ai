from typing import Any, Protocol

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job


class JobApplier(Protocol):
    """A way of applying to a job (email, a given platform's form)."""

    name: str

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        """Apply to the job and return the outcome.

        Raises a typed `JobHunterError` when the attempt fails for a reason the
        caller must know about (bad input, transport failure). The use case
        records the failed attempt before letting the error propagate, so a
        failure is never silent and never invisible in the history.
        """
        ...
