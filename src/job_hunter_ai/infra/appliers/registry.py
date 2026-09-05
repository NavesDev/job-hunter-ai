"""Resolves a `JobApplier` for a `(method, source)` pair.

`email` is generic (`*`): it works for a job from any platform. A form applier is
registered per platform, because every site's form is different.
"""

from collections.abc import Callable, Iterable, Mapping

from job_hunter_ai.domain.ports.job_applier import JobApplier

ApplierFactory = Callable[[], JobApplier]
ANY_SOURCE = "*"


class ApplierRegistry:
    """Maps `(method, source)` to a factory, falling back to the generic `*` source."""

    def __init__(self, factories: Mapping[tuple[str, str], ApplierFactory]) -> None:
        self._factories = dict(factories)

    def register(self, method: str, source: str, factory: ApplierFactory) -> None:
        self._factories[(method, source)] = factory

    def available(self) -> Iterable[tuple[str, str]]:
        return sorted(self._factories)

    def get(self, method: str, source: str) -> JobApplier | None:
        """Return the applier for the pair, or `None` when nothing is registered.

        `None` is not an error: applying is then reported as `skipped`.
        """
        factory = self._factories.get((method, source)) or self._factories.get((method, ANY_SOURCE))
        return factory() if factory else None
