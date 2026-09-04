from typing import Protocol

from job_hunter_ai.domain.ports.job_applier import JobApplier


class ApplierRegistry(Protocol):
    """Resolves the applier for a `(method, source)` pair.

    Returning `None` is a valid answer, not a failure: with no applier for the
    pair, applying is `skipped` (docs/ARCHITECTURE.md#registries-strategy-resolution).
    """

    def get(self, method: str, source: str) -> JobApplier | None: ...
