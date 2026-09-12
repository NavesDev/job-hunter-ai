"""Resolves the `RequirementsExtractor` of a source (Open/Closed: a platform is an entry).

Unlike the applier registry, this one always answers: a posting the tool knows nothing
about still has a description, and the generic extractor reads it.
"""

from collections.abc import Callable, Iterable, Mapping

from job_hunter_ai.domain.ports.requirements_extractor import RequirementsExtractor
from job_hunter_ai.infra.requirements.geekhunter_requirements import (
    GeekHunterRequirementsExtractor,
)
from job_hunter_ai.infra.requirements.generic_requirements import GenericRequirementsExtractor

ExtractorFactory = Callable[[], RequirementsExtractor]

DEFAULT_EXTRACTORS: Mapping[str, ExtractorFactory] = {
    GeekHunterRequirementsExtractor.name: GeekHunterRequirementsExtractor,
}


class ExtractorRegistry:
    """Maps a job's `source` to the factory that builds its requirements extractor."""

    def __init__(
        self,
        factories: Mapping[str, ExtractorFactory] | None = None,
        fallback: ExtractorFactory = GenericRequirementsExtractor,
    ) -> None:
        self._factories: dict[str, ExtractorFactory] = dict(
            DEFAULT_EXTRACTORS if factories is None else factories
        )
        self._fallback = fallback

    def register(self, source: str, factory: ExtractorFactory) -> None:
        self._factories[source] = factory

    def available(self) -> Iterable[str]:
        return sorted(self._factories)

    def get(self, source: str) -> RequirementsExtractor:
        return self._factories.get(source, self._fallback)()
