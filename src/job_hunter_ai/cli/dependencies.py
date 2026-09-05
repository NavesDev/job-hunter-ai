"""The composition root: builds the concrete dependency graph for the commands.

`cli/` is the only layer allowed to know which implementation sits behind a port
(docs/CODE_STANDARDS.md#architecture-dependency-rule). The applier factories are
lazy, so a command never pays for — nor fails on — a dependency it does not use:
`list-jobs` and `--method form` never touch the SMTP credentials.
"""

from pathlib import Path

from job_hunter_ai.config.credentials import load_smtp_config
from job_hunter_ai.infra.appliers.email_applier import EmailApplier
from job_hunter_ai.infra.appliers.registry import ANY_SOURCE, ApplierRegistry
from job_hunter_ai.infra.sources.registry import SourceRegistry


def build_source_registry() -> SourceRegistry:
    return SourceRegistry()


def build_applier_registry(root: Path | None = None) -> ApplierRegistry:
    def email_applier() -> EmailApplier:
        return EmailApplier(load_smtp_config(root))

    return ApplierRegistry({(EmailApplier.name, ANY_SOURCE): email_applier})
