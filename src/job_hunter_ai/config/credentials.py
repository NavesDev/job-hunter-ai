"""SMTP credentials, always from `.env` — never from the versioned YAML.

Kept in its own module so that `list-jobs` and the form appliers never trigger a
credential lookup they do not need (docs/ARCHITECTURE.md#configuration-vs-credentials).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from job_hunter_ai.domain.entities.smtp_config import SmtpConfig
from job_hunter_ai.domain.errors import InvalidInputError

ENV_FILE = ".env"
REQUIRED_VARIABLES = ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD")
DEFAULT_PORT = 587
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def load_smtp_config(root: Path | None = None) -> SmtpConfig:
    """Read the SMTP settings from `.env` (or the process environment).

    Fail-fast: a missing host, username or password raises here rather than at
    the moment the connection is attempted.
    """
    base = root or Path.cwd()
    load_dotenv(base / ENV_FILE, override=False)
    missing = [name for name in REQUIRED_VARIABLES if not os.environ.get(name)]
    if missing:
        raise InvalidInputError(
            f"missing SMTP credentials in {base / ENV_FILE}: {', '.join(missing)}"
        )
    return SmtpConfig(
        host=os.environ["SMTP_HOST"],
        port=_port(os.environ.get("SMTP_PORT")),
        username=os.environ["SMTP_USERNAME"],
        password=os.environ["SMTP_PASSWORD"],
        use_tls=(os.environ.get("SMTP_USE_TLS", "true").strip().lower() in _TRUE_VALUES),
    )


def _port(raw: str | None) -> int:
    if raw is None or not raw.strip():
        return DEFAULT_PORT
    try:
        return int(raw)
    except ValueError as exc:
        raise InvalidInputError(f"SMTP_PORT must be an integer, got `{raw}`") from exc
