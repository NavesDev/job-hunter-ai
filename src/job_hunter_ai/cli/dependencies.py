"""The composition root: builds the concrete dependency graph for the commands.

`cli/` is the only layer allowed to know which implementation sits behind a port
(docs/CODE_STANDARDS.md#architecture-dependency-rule). The applier factories are
lazy, so a command never pays for — nor fails on — a dependency it does not use:
`list-jobs` and `--method form` never touch the SMTP credentials.
"""

from pathlib import Path
from typing import Any

from job_hunter_ai.config.credentials import load_platform_credentials, load_smtp_config
from job_hunter_ai.config.sources import load_source_settings
from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.infra.appliers.email_applier import EmailApplier
from job_hunter_ai.infra.appliers.geekhunter_form import GeekHunterFormApplier
from job_hunter_ai.infra.appliers.registry import ANY_SOURCE, ApplierRegistry
from job_hunter_ai.infra.sessions.geekhunter_session import (
    DEFAULT_BASE_URL as GEEKHUNTER_BASE_URL,
)
from job_hunter_ai.infra.sessions.geekhunter_session import GeekHunterSession
from job_hunter_ai.infra.sessions.geekhunter_sign_in import GeekHunterSignIn
from job_hunter_ai.infra.sessions.registry import SessionRegistry
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
        settings = load_source_settings(GeekHunterJobSource.name, root)
        return GeekHunterFormApplier(settings, _geekhunter_sign_in(settings, root))

    return ApplierRegistry(
        {
            (EmailApplier.name, ANY_SOURCE): email_applier,
            ("form", GeekHunterJobSource.name): geekhunter_form_applier,
        }
    )


def _geekhunter_sign_in(settings: dict[str, Any], root: Path | None) -> GeekHunterSignIn | None:
    """The sign-in the applier uses when a job page treats it as a stranger.

    `None` when the profile has no credentials: applying anonymously still works, and a
    missing credential is not a reason to refuse an application the caller asked for.
    """
    try:
        credentials = load_platform_credentials(GeekHunterJobSource.name, root)
    except InvalidInputError:
        return None
    base_url = str(settings.get("base_url") or GEEKHUNTER_BASE_URL).rstrip("/")
    return GeekHunterSignIn(credentials, base_url, int(settings.get("timeout_ms", 30_000)))


def build_session_registry(root: Path | None = None) -> SessionRegistry:
    """The strategies that keep a platform session, each with its own credentials."""

    def geekhunter_session() -> GeekHunterSession:
        return GeekHunterSession(
            load_platform_credentials(GeekHunterJobSource.name, root),
            load_source_settings(GeekHunterJobSource.name, root),
        )

    return SessionRegistry({GeekHunterJobSource.name: geekhunter_session})
