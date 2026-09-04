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

from job_hunter_ai.domain.errors import InvalidInputError

CONFIG_PATH_ENV = "JOB_HUNTER_AI_CONFIG"
LOCAL_CONFIG = Path("config/local/config.yaml")
EXAMPLE_CONFIG = Path("config/config.example.yaml")
DEFAULT_DATABASE_PATH = Path("config/local/jobs.db")


@dataclass(frozen=True, slots=True)
class StorageConfig:
    database_path: Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    storage: StorageConfig


def load_config(root: Path | None = None) -> AppConfig:
    """Assemble the configuration, resolving relative paths against the repository root."""
    base = root or Path.cwd()
    path = resolve_config_path(base)
    raw = _read_yaml(path)
    return AppConfig(storage=_storage_from(raw, base))


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
    section = raw.get("storage") or {}
    if not isinstance(section, dict):
        raise InvalidInputError("`storage` must be a mapping")
    configured = section.get("database_path") or DEFAULT_DATABASE_PATH
    database_path = Path(configured)
    if not database_path.is_absolute():
        database_path = base / database_path
    return StorageConfig(database_path=database_path)
