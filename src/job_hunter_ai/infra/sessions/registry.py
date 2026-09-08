"""Resolves a `SessionStrategy` by source name (a new platform is a new entry here)."""

from collections.abc import Callable, Iterable, Mapping

from job_hunter_ai.domain.errors import SourceNotFoundError
from job_hunter_ai.domain.ports.session_strategy import SessionStrategy

StrategyFactory = Callable[[], SessionStrategy]


class SessionRegistry:
    """Maps a `--source` value to the strategy that keeps its session."""

    def __init__(self, factories: Mapping[str, StrategyFactory] | None = None) -> None:
        self._factories: dict[str, StrategyFactory] = dict(factories or {})

    def register(self, name: str, factory: StrategyFactory) -> None:
        self._factories[name] = factory

    def available(self) -> Iterable[str]:
        return sorted(self._factories)

    def get(self, name: str) -> SessionStrategy:
        """Build the strategy registered under `name`, failing fast when there is none."""
        try:
            factory = self._factories[name]
        except KeyError as exc:
            known = ", ".join(self.available()) or "none"
            raise SourceNotFoundError(
                f"no session strategy for source `{name}`; available: {known}"
            ) from exc
        return factory()
