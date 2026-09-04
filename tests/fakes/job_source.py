"""In-memory `JobSource` fakes, preferred over Mock() when behavior matters."""

from typing import Any

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.job_id import build_job_id
from job_hunter_ai.domain.time_utils import utc_now


def build_job(
    title: str = "Backend Engineer",
    company: str = "Acme",
    source: str = "manual",
    **overrides: Any,
) -> Job:
    url = overrides.pop("url", f"https://{company.lower()}.com/jobs/1")
    return Job(
        id=overrides.pop("id", build_job_id(source, url=url, company=company, title=title)),
        source=source,
        title=title,
        company=company,
        description=overrides.pop("description", "Python, SQL"),
        url=url,
        apply_email=overrides.pop("apply_email", "jobs@acme.com"),
        raw=overrides.pop("raw", {}),
        collected_at=overrides.pop("collected_at", utc_now()),
    )


class FakeJobSource:
    name = "fake"

    def __init__(self, jobs: list[Job] | None = None):
        self.jobs = jobs if jobs is not None else [build_job()]
        self.calls: list[dict[str, Any]] = []

    def fetch(self, max_length: int, **options: Any) -> list[Job]:
        self.calls.append({"max_length": max_length, **options})
        return self.jobs[:max_length]


class ExplodingJobSource:
    name = "exploding"

    def __init__(self, error: Exception):
        self.error = error

    def fetch(self, max_length: int, **options: Any) -> list[Job]:
        raise self.error
