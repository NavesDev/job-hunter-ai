"""CLI output formatting. The only place that writes to stdout/stderr.

Rules live in docs/CONTRACT.md: stdout carries success JSON only, stderr carries
error JSON, and failures exit with a non-zero code.
"""

import json
import sys
from typing import Any, NoReturn

from job_hunter_ai.domain.errors import JobHunterError


def emit_success(payload: Any) -> None:
    """Print the success JSON to stdout."""
    json.dump(payload, sys.stdout, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def emit_error(error: JobHunterError, exit_code: int = 1) -> NoReturn:
    """Print the error JSON to stderr and exit with a non-zero code."""
    json.dump({"error": str(error), "code": error.code}, sys.stderr, ensure_ascii=False)
    sys.stderr.write("\n")
    raise SystemExit(exit_code)
