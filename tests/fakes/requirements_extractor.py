"""In-memory `RequirementsExtractor` and its registry, for the use case tests."""

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.job_requirements import JobRequirements


class FakeRequirementsExtractor:
    name = "fake"

    def __init__(self, requirements: JobRequirements | None = None):
        self.requirements = requirements or JobRequirements(required=("python",))
        self.calls: list[Job] = []

    def extract(self, job: Job) -> JobRequirements:
        self.calls.append(job)
        return self.requirements


class FakeExtractorRegistry:
    def __init__(self, extractor: FakeRequirementsExtractor | None = None):
        self.extractor = extractor or FakeRequirementsExtractor()
        self.sources: list[str] = []

    def get(self, source: str) -> FakeRequirementsExtractor:
        self.sources.append(source)
        return self.extractor
