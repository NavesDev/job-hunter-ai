"""Use case: apply to an already collected job through the resolved applier."""

from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import InvalidInputError, JobHunterError, JobNotFoundError
from job_hunter_ai.domain.ports.applier_registry import ApplierRegistry
from job_hunter_ai.domain.ports.job_repository import JobRepository
from job_hunter_ai.domain.time_utils import utc_now

NO_APPLIER = "none"


class ApplyJobUseCase:
    """Applies to one job and records the attempt, whatever its outcome.

    The history is append-only: a failure is persisted before the error is allowed
    to propagate, so no attempt is ever invisible (docs/DATA_MODEL.md).
    """

    def __init__(
        self,
        repository: JobRepository,
        appliers: ApplierRegistry,
        profile: CandidateProfile,
    ) -> None:
        self._repository = repository
        self._appliers = appliers
        self._profile = profile

    def execute(self, job_id: str, method: str, **options: Any) -> ApplicationResult:
        job = self._require_job(job_id)
        applier = self._appliers.get(method, job.source)
        if applier is None:
            return self._record(self._skipped(job, method))
        try:
            result = applier.apply(job, self._profile, **options)
        except JobHunterError as error:
            self._record(self._failed(job, method, applier.name, str(error)))
            raise
        return self._record(result)

    def _require_job(self, job_id: str) -> Job:
        if not job_id or not job_id.strip():
            raise InvalidInputError("--job-id is required")
        job = self._repository.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"no job with id `{job_id}`; run list-jobs first")
        return job

    def _record(self, result: ApplicationResult) -> ApplicationResult:
        self._repository.save_application(result)
        return result

    def _skipped(self, job: Job, method: str) -> ApplicationResult:
        return ApplicationResult(
            job_id=job.id,
            method=method,
            status=ApplicationStatus.SKIPPED,
            applier=NO_APPLIER,
            detail=f"no applier registered for method=`{method}` source=`{job.source}`",
            applied_at=utc_now(),
        )

    def _failed(self, job: Job, method: str, applier: str, detail: str) -> ApplicationResult:
        return ApplicationResult(
            job_id=job.id,
            method=method,
            status=ApplicationStatus.FAILED,
            applier=applier,
            detail=detail,
            applied_at=utc_now(),
        )
