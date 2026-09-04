"""CLI entrypoints: `list-jobs` and `apply-job`.

The commands only parse flags, assemble the concrete dependency graph and format
the output — every rule lives in `application/`, `domain/` and `infra/`.
"""

from pathlib import Path
from typing import Annotated

import typer

from job_hunter_ai.application.list_jobs import DEFAULT_MAX_LENGTH, ListJobsUseCase
from job_hunter_ai.cli.output import contract_command, emit_error, emit_success
from job_hunter_ai.cli.serializers import job_to_payload
from job_hunter_ai.config.loader import load_config
from job_hunter_ai.domain.errors import NotImplementedYetError
from job_hunter_ai.infra.repository.sqlite_job_repository import SqliteJobRepository
from job_hunter_ai.infra.sources.registry import SourceRegistry

list_jobs_app = typer.Typer(add_completion=False, help="List jobs from a registered source.")
apply_job_app = typer.Typer(add_completion=False, help="Apply to an already listed job.")


@list_jobs_app.command()
@contract_command
def list_jobs(
    source: Annotated[str, typer.Option("--source", help="Registered job source.")],
    file: Annotated[Path | None, typer.Option("--file", help="Input file (manual source).")] = None,
    max_length: Annotated[
        int, typer.Option("--max-length", help="Maximum number of jobs returned.")
    ] = DEFAULT_MAX_LENGTH,
) -> None:
    """List normalized jobs from a source and print them as JSON on stdout."""
    config = load_config()
    job_source = SourceRegistry().get(source)
    with SqliteJobRepository(config.storage.database_path) as repository:
        jobs = ListJobsUseCase(job_source, repository).execute(max_length=max_length, file=file)
    emit_success([job_to_payload(job) for job in jobs])


@apply_job_app.command()
def apply_job(
    method: Annotated[str, typer.Option("--method", help="Application method: email or form.")],
    job_id: Annotated[
        str | None, typer.Option("--job-id", help="Job id returned by list-jobs.")
    ] = None,
    email: Annotated[
        str | None, typer.Option("--email", help="Recipient of the application.")
    ] = None,
    subject: Annotated[str | None, typer.Option("--subject", help="Email subject.")] = None,
    all_ready: Annotated[
        bool, typer.Option("--all-ready", help="Apply in batch to every collected job.")
    ] = False,
) -> None:
    """Apply to an already listed job and print the result as JSON on stdout."""
    emit_error(NotImplementedYetError("apply-job is not implemented yet (Sprint 01, TASK-02)"))
