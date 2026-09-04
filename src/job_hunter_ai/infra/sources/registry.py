"""Resolves a `JobSource` by name (Open/Closed: a new platform is a new entry here).

Keeping the registry in `infra/` is what lets `application/` stay unaware of any
concrete source — the CLI resolves the strategy and injects it.
"""

from collections.abc import Callable, Iterable, Mapping

from job_hunter_ai.domain.errors import SourceNotFoundError
from job_hunter_ai.domain.ports.job_source import JobSource
from job_hunter_ai.infra.sources.manual_json import ManualJsonJobSource

SourceFactory = Callable[[], JobSource]

DEFAULT_SOURCES: Mapping[str, SourceFactory] = {
    ManualJsonJobSource.name: ManualJsonJobSource,
}


class SourceRegistry:
    """Maps a `--source` value to the factory that builds its implementation."""

    def __init__(self, factories: Mapping[str, SourceFactory] | None = None) -> None:
        self._factories: dict[str, SourceFactory] = dict(
            DEFAULT_SOURCES if factories is None else factories
        )

    def register(self, name: str, factory: SourceFactory) -> None:
        self._factories[name] = factory

    def available(self) -> Iterable[str]:
        return sorted(self._factories)

    def get(self, name: str) -> JobSource:
        """Build the source registered under `name`, failing fast when there is none."""
        try:
            factory = self._factories[name]
        except KeyError as exc:
            known = ", ".join(self.available())
            raise SourceNotFoundError(f"unknown source `{name}`; available: {known}") from exc
        return factory()
