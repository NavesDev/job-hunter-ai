"""Loads the non-sensitive configuration (YAML) into typed objects.

Credentials never come from here — they live in `.env` (docs/ARCHITECTURE.md).
Fail-fast: a missing or malformed file raises `InvalidInputError` at load time
instead of letting a `None` travel into a use case.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.errors import InvalidInputError

CONFIG_PATH_ENV = "JOB_HUNTER_AI_CONFIG"
LOCAL_CONFIG = Path("config/local/config.yaml")
EXAMPLE_CONFIG = Path("config/config.example.yaml")
DEFAULT_DATABASE_PATH = Path("config/local/jobs.db")
DEFAULT_RESUME_PATH = Path("config/local/resume.pdf")
DEFAULT_EMAIL_BODY_PATH = Path("config/local/email-body.html")
DEFAULT_SUBJECT = "Application - {title}"


@dataclass(frozen=True, slots=True)
class StorageConfig:
    database_path: Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    storage: StorageConfig
    candidate: CandidateProfile


def load_config(root: Path | None = None) -> AppConfig:
    """Assemble the configuration, resolving relative paths against the repository root."""
    base = root or Path.cwd()
    path = resolve_config_path(base)
    raw = _read_yaml(path)
    return AppConfig(storage=_storage_from(raw, base), candidate=_candidate_from(raw, base))


def resolve_config_path(base: Path) -> Path:
    """`$JOB_HUNTER_AI_CONFIG`, then the local file, then the versioned example."""
    override = os.environ.get(CONFIG_PATH_ENV)
    if override:
        return Path(override)
    local = base / LOCAL_CONFIG
    return local if local.is_file() else base / EXAMPLE_CONFIG


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InvalidInputError(f"configuration file not found: {path}")
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f"invalid YAML in {path}: {exc}") from exc
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise InvalidInputError(f"{path} must contain a mapping at the top level")
    return parsed


def _storage_from(raw: dict[str, Any], base: Path) -> StorageConfig:
    section = _mapping(raw, "storage")
    return StorageConfig(
        database_path=_resolve(base, section.get("database_path"), DEFAULT_DATABASE_PATH)
    )


def _candidate_from(raw: dict[str, Any], base: Path) -> CandidateProfile:
    candidate = _mapping(raw, "candidate")
    application = _mapping(raw, "application")
    return CandidateProfile(
        name=str(candidate.get("name") or ""),
        contact_email=str(candidate.get("contact_email") or ""),
        resume_path=_resolve(base, application.get("resume_path"), DEFAULT_RESUME_PATH),
        email_body_path=_resolve(base, application.get("email_body_path"), DEFAULT_EMAIL_BODY_PATH),
        default_subject=str(application.get("default_subject") or DEFAULT_SUBJECT),
        extra_fields={
            key: str(value) for key, value in _mapping(candidate, "extra_fields").items()
        },
    )


def _mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    section = raw.get(key) or {}
    if not isinstance(section, dict):
        raise InvalidInputError(f"`{key}` must be a mapping")
    return section


def _resolve(base: Path, configured: Any, default: Path) -> Path:
    path = Path(str(configured)) if configured else default
    return path if path.is_absolute() else base / path
