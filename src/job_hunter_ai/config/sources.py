"""Per-platform, non-sensitive settings: `config/local/sources/<platform>.yaml`.

Filters, base URLs and timeouts live here; a platform credential never does — those
stay in `.env` with a platform prefix (docs/ARCHITECTURE.md#configuration-vs-credentials).
A platform with nothing to configure simply has no file, and gets `{}`.
"""

from pathlib import Path
from typing import Any

import yaml

from job_hunter_ai.domain.errors import InvalidInputError

SOURCES_DIR = Path("config/local/sources")


def source_settings_path(name: str, root: Path | None = None) -> Path:
    return (root or Path.cwd()) / SOURCES_DIR / f"{name}.yaml"


def load_source_settings(name: str, root: Path | None = None) -> dict[str, Any]:
    """The platform's settings mapping, or `{}` when the platform has no file."""
    path = source_settings_path(name, root)
    if not path.is_file():
        return {}
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f"invalid YAML in {path}: {exc}") from exc
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise InvalidInputError(f"{path} must contain a mapping at the top level")
    return parsed
