"""Use case: score an already collected job against the candidate's résumé."""

from pathlib import Path

from job_hunter_ai.domain.entities.ats_score import AtsScore
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import InvalidInputError, JobNotFoundError
from job_hunter_ai.domain.matching.ats_scorer import AtsScorer
from job_hunter_ai.domain.ports.extractor_registry import ExtractorRegistry
from job_hunter_ai.domain.ports.job_repository import JobRepository
from job_hunter_ai.domain.ports.resume_reader import ResumeReader


class ScoreJobUseCase:
    """Simulates the screening a company's ATS runs before a human ever sees the résumé.

    Read-only on purpose: it reaches no platform and records nothing. The score is an
    opinion about a file and a posting, and it changes whenever either of them does.
    """

    def __init__(
        self,
        repository: JobRepository,
        extractors: ExtractorRegistry,
        resume_reader: ResumeReader,
        scorer: AtsScorer,
    ) -> None:
        self._repository = repository
        self._extractors = extractors
        self._resume_reader = resume_reader
        self._scorer = scorer

    def execute(self, job_id: str, resume_path: Path) -> AtsScore:
        job = self._require_job(job_id)
        requirements = self._extractors.get(job.source).extract(job)
        resume = self._resume_reader.read(resume_path)
        return self._scorer.score(job, requirements, resume)

    def _require_job(self, job_id: str) -> Job:
        if not job_id or not job_id.strip():
            raise InvalidInputError("--job-id is required")
        job = self._repository.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"no job with id `{job_id}`; run list-jobs first")
        return job
