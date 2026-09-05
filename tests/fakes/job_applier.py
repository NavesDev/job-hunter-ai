"""In-memory `JobApplier` and `ApplierRegistry` fakes."""

from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.ports.job_applier import JobApplier
from job_hunter_ai.domain.time_utils import utc_now


class FakeJobApplier:
    def __init__(self, name: str = "email", error: Exception | None = None):
        self.name = name
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        self.calls.append({"job": job, "profile": profile, **options})
        if self.error is not None:
            raise self.error
        return ApplicationResult(
            job_id=job.id,
            method=self.name,
            status=ApplicationStatus.SENT,
            applier=self.name,
            detail="sent",
            applied_at=utc_now(),
        )


class FakeApplierRegistry:
    """Returns the applier it was given, or None to force the `skipped` path."""

    def __init__(self, applier: JobApplier | None = None):
        self.applier = applier
        self.calls: list[tuple[str, str]] = []

    def get(self, method: str, source: str) -> JobApplier | None:
        self.calls.append((method, source))
        return self.applier
