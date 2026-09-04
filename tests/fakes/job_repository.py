"""In-memory `JobRepository` fake honoring the deduplication contract."""

from dataclasses import replace

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.job import Job


class FakeJobRepository:
    def __init__(self):
        self.jobs: dict[str, Job] = {}
        self.applications: list[ApplicationResult] = []

    def save_jobs(self, jobs: list[Job]) -> list[Job]:
        for job in jobs:
            existing = self.jobs.get(job.id)
            collected_at = existing.collected_at if existing else job.collected_at
            self.jobs[job.id] = replace(job, collected_at=collected_at)
        return [self.jobs[job.id] for job in jobs]

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def save_application(self, result: ApplicationResult) -> None:
        self.applications.append(result)
