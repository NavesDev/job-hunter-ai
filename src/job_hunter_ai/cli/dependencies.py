"""The composition root: builds the concrete dependency graph for the commands.

`cli/` is the only layer allowed to know which implementation sits behind a port
(docs/CODE_STANDARDS.md#architecture-dependency-rule). The applier factories are
lazy, so a command never pays for — nor fails on — a dependency it does not use:
`list-jobs` and `--method form` never touch the SMTP credentials.
"""

from pathlib import Path

from job_hunter_ai.config.credentials import load_smtp_config
from job_hunter_ai.config.sources import load_source_settings
from job_hunter_ai.infra.appliers.email_applier import EmailApplier
from job_hunter_ai.infra.appliers.geekhunter_form import GeekHunterFormApplier
from job_hunter_ai.infra.appliers.registry import ANY_SOURCE, ApplierRegistry
from job_hunter_ai.infra.sources.geekhunter import GeekHunterJobSource, UrllibHttpClient
from job_hunter_ai.infra.sources.registry import SourceRegistry


def build_source_registry(root: Path | None = None) -> SourceRegistry:
    """The default registry, with every platform-configured source rewired to its settings."""
    registry = SourceRegistry()
    registry.register(GeekHunterJobSource.name, lambda: _geekhunter_source(root))
    return registry


def _geekhunter_source(root: Path | None) -> GeekHunterJobSource:
    settings = load_source_settings(GeekHunterJobSource.name, root)
    http = settings.get("http") or {}
    client = UrllibHttpClient(**{key: value for key, value in http.items() if key in _HTTP_OPTIONS})
    return GeekHunterJobSource(client, settings=settings)


_HTTP_OPTIONS = frozenset({"user_agent", "timeout_seconds", "min_request_interval_seconds"})


def build_applier_registry(root: Path | None = None) -> ApplierRegistry:
    def email_applier() -> EmailApplier:
        return EmailApplier(load_smtp_config(root))

    def geekhunter_form_applier() -> GeekHunterFormApplier:
        return GeekHunterFormApplier(load_source_settings(GeekHunterJobSource.name, root))

    return ApplierRegistry(
        {
            (EmailApplier.name, ANY_SOURCE): email_applier,
            ("form", GeekHunterJobSource.name): geekhunter_form_applier,
        }
    )
