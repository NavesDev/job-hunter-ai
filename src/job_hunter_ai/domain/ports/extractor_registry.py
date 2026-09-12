from typing import Protocol

from job_hunter_ai.domain.ports.requirements_extractor import RequirementsExtractor


class ExtractorRegistry(Protocol):
    """Resolves the requirements extractor for a job source.

    An unknown source is not a failure: every posting has a description, so the registry
    always answers with an extractor (docs/ARCHITECTURE.md#registries-strategy-resolution).
    """

    def get(self, source: str) -> RequirementsExtractor: ...
