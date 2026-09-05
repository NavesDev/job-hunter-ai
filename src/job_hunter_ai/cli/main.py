"""CLI entrypoints: `list-jobs` and `apply-job`.

The commands only parse flags, assemble the concrete dependency graph and format
the output — every rule lives in `application/`, `domain/` and `infra/`.
"""

from pathlib import Path
from typing import Annotated

import typer

from job_hunter_ai.application.apply_job import ApplyJobUseCase
from job_hunter_ai.application.list_jobs import DEFAULT_MAX_LENGTH, ListJobsUseCase
from job_hunter_ai.cli.dependencies import build_applier_registry, build_source_registry
from job_hunter_ai.cli.output import contract_command, emit_success
from job_hunter_ai.cli.serializers import application_result_to_payload, job_to_payload
from job_hunter_ai.config.loader import load_config
from job_hunter_ai.domain.errors import ApplierNotFoundError, InvalidInputError
from job_hunter_ai.infra.repository.sqlite_job_repository import SqliteJobRepository

SUPPORTED_METHODS = ("email", "form")

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
    job_source = build_source_registry().get(source)
    with SqliteJobRepository(config.storage.database_path) as repository:
        jobs = ListJobsUseCase(job_source, repository).execute(max_length=max_length, file=file)
    emit_success([job_to_payload(job) for job in jobs])


@apply_job_app.command()
@contract_command
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
    if all_ready:
        raise InvalidInputError("--all-ready is not supported yet; apply one --job-id at a time")
    if method not in SUPPORTED_METHODS:
        raise ApplierNotFoundError(
            f"unknown --method `{method}`; supported: {', '.join(SUPPORTED_METHODS)}"
        )
    config = load_config()
    with SqliteJobRepository(config.storage.database_path) as repository:
        use_case = ApplyJobUseCase(repository, build_applier_registry(), config.candidate)
        result = use_case.execute(job_id or "", method, email=email, subject=subject)
    emit_success(application_result_to_payload(result))
