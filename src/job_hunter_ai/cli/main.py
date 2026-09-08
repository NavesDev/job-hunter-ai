"""CLI entrypoints: `list-jobs` and `apply-job`.

The commands only parse flags, assemble the concrete dependency graph and format
the output — every rule lives in `application/`, `domain/` and `infra/`.
"""

from pathlib import Path
from typing import Annotated

import typer

from job_hunter_ai.application.apply_job import ApplyJobUseCase
from job_hunter_ai.application.list_jobs import DEFAULT_MAX_LENGTH, ListJobsUseCase
from job_hunter_ai.application.login import LoginUseCase
from job_hunter_ai.cli.dependencies import (
    build_applier_registry,
    build_session_registry,
    build_source_registry,
)
from job_hunter_ai.cli.output import contract_command, emit_success
from job_hunter_ai.cli.serializers import (
    application_result_to_payload,
    job_to_payload,
    session_result_to_payload,
)
from job_hunter_ai.config.loader import load_config
from job_hunter_ai.domain.errors import ApplierNotFoundError, InvalidInputError
from job_hunter_ai.infra.appliers.geekhunter_salary import KINDS as SALARY_KINDS
from job_hunter_ai.infra.repository.sqlite_job_repository import SqliteJobRepository

SUPPORTED_METHODS = ("email", "form")

list_jobs_app = typer.Typer(add_completion=False, help="List jobs from a registered source.")
apply_job_app = typer.Typer(add_completion=False, help="Apply to an already listed job.")
login_app = typer.Typer(
    add_completion=False, help="Sign the tool's browser profile into a platform."
)


@list_jobs_app.command()
@contract_command
def list_jobs(
    source: Annotated[str, typer.Option("--source", help="Registered job source.")],
    file: Annotated[Path | None, typer.Option("--file", help="Input file (manual source).")] = None,
    max_length: Annotated[
        int, typer.Option("--max-length", help="Maximum number of jobs returned.")
    ] = DEFAULT_MAX_LENGTH,
    filter_: Annotated[
        list[str] | None,
        typer.Option(
            "--filter",
            help="Listing filter as `name=value`; repeat it. Replaces the filters in the YAML.",
        ),
    ] = None,
) -> None:
    """List normalized jobs from a source and print them as JSON on stdout."""
    filters = _pairs("--filter", filter_)
    config = load_config()
    job_source = build_source_registry().get(source)
    with SqliteJobRepository(config.storage.database_path) as repository:
        jobs = ListJobsUseCase(job_source, repository).execute(
            max_length=max_length, file=file, filters=filters
        )
    emit_success([job_to_payload(job) for job in jobs])


def _pairs(flag: str, given: list[str] | None) -> dict[str, str]:
    """Parse every `<flag> name=value` into a mapping, refusing anything else.

    Only the syntax is checked here: which names and values are meaningful belongs to
    the source or the applier, and each raises before it touches the platform.
    """
    pairs: dict[str, str] = {}
    for pair in given or []:
        name, separator, value = pair.partition("=")
        if not separator or not name.strip():
            raise InvalidInputError(f"{flag} takes `name=value`, got `{pair}`")
        pairs[name.strip()] = value.strip()
    return pairs


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
    salary: Annotated[
        str | None,
        typer.Option(
            "--salary",
            help="Which predefined salary expectation to offer: clt, pj or internship.",
        ),
    ] = None,
    answer: Annotated[
        list[str] | None,
        typer.Option(
            "--answer",
            help="Screening answer as `question-id=value`; repeat it, one per question.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Apply again to a job already applied to, on purpose."),
    ] = False,
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
    if salary is not None and salary.strip().lower() not in SALARY_KINDS:
        raise InvalidInputError(
            f"unknown --salary `{salary}`; it names a predefined expectation, not an amount: "
            f"{', '.join(SALARY_KINDS)}"
        )
    config = load_config()
    with SqliteJobRepository(config.storage.database_path) as repository:
        use_case = ApplyJobUseCase(repository, build_applier_registry(), config.candidate)
        result = use_case.execute(
            job_id or "",
            method,
            email=email,
            subject=subject,
            salary=salary,
            answers=_pairs("--answer", answer),
            force=force,
        )
    emit_success(application_result_to_payload(result))


@login_app.command()
@contract_command
def login(
    source: Annotated[str, typer.Option("--source", help="Platform to sign in to.")],
    force: Annotated[
        bool, typer.Option("--force", help="Sign in again even when the profile has a session.")
    ] = False,
) -> None:
    """Make sure the tool's browser profile holds a session for the platform.

    The credentials come from `.env` and are never printed, logged or recorded.
    """
    strategy = build_session_registry().get(source)
    result = LoginUseCase(strategy).execute(force=force)
    emit_success(session_result_to_payload(result))
