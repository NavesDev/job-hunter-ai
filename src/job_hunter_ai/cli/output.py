"""CLI output formatting. The only place that writes to stdout/stderr.

Rules live in docs/CONTRACT.md: stdout carries success JSON only, stderr carries
error JSON, and failures exit with a non-zero code.
"""

import functools
import json
import sys
from collections.abc import Callable
from typing import Any, NoReturn, ParamSpec

from job_hunter_ai.domain.errors import JobHunterError

P = ParamSpec("P")


def emit_success(payload: Any) -> None:
    """Print the success JSON to stdout."""
    json.dump(payload, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def emit_error(error: JobHunterError, exit_code: int = 1) -> NoReturn:
    """Print the error JSON to stderr and exit with a non-zero code."""
    json.dump({"error": str(error), "code": error.code}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    raise SystemExit(exit_code)


def contract_command(command: Callable[P, None]) -> Callable[P, None]:
    """Turn any typed domain error into the contract's error JSON plus a failing exit code.

    This is the single boundary where an exception stops being a Python object and
    becomes the CLI contract — no stack trace ever reaches the calling agent.
    """

    @functools.wraps(command)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            command(*args, **kwargs)
        except JobHunterError as error:
            emit_error(error)

    return wrapper
