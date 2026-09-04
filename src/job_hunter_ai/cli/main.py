"""CLI entrypoints: `list-jobs` and `apply-job`.

Sprint 01 skeleton: the commands exist and declare the flag contract from
docs/CONTRACT.md, failing with `NOT_IMPLEMENTED` until each task is delivered.
"""

from pathlib import Path
from typing import Annotated

import typer

from job_hunter_ai.cli.output import emit_error
from job_hunter_ai.domain.errors import NotImplementedYetError

list_jobs_app = typer.Typer(add_completion=False, help="List jobs from a registered source.")
apply_job_app = typer.Typer(add_completion=False, help="Apply to an already listed job.")


@list_jobs_app.command()
def list_jobs(
    source: Annotated[str, typer.Option("--source", help="Registered job source.")],
    file: Annotated[Path | None, typer.Option("--file", help="Input file (manual source).")] = None,
    max_length: Annotated[
        int, typer.Option("--max-length", help="Maximum number of jobs returned.")
    ] = 50,
) -> None:
    """List normalized jobs from a source and print them as JSON on stdout."""
    emit_error(NotImplementedYetError("list-jobs is not implemented yet (Sprint 01, TASK-01)"))


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
