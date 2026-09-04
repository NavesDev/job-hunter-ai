"""The `manual` source: a JSON file written by hand or by an orchestrating agent."""

import json
from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.domain.job_id import build_job_id
from job_hunter_ai.domain.time_utils import utc_now

REQUIRED_FIELDS = ("title", "company")
_KNOWN_FIELDS = frozenset({"title", "company", "description", "url", "apply_email", "external_id"})


class ManualJsonJobSource:
    """Reads a list of job objects from a JSON file and normalizes it into `Job`s."""

    name = "manual"

    def fetch(self, max_length: int, **options: Any) -> list[Job]:
        path = self._required_path(options.get("file"))
        entries = self._read_entries(path)
        collected_at = utc_now()
        return [self._to_job(entry, index, collected_at) for index, entry in enumerate(entries)][
            :max_length
        ]

    def _required_path(self, raw: Any) -> Path:
        if raw is None:
            raise InvalidInputError("the manual source requires --file")
        return Path(raw)

    def _read_entries(self, path: Path) -> list[Any]:
        if not path.is_file():
            raise InvalidInputError(f"input file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidInputError(f"invalid JSON in {path}: {exc}") from exc
        if not isinstance(payload, list):
            raise InvalidInputError(f"{path} must contain a JSON list of jobs")
        return payload

    def _to_job(self, entry: Any, index: int, collected_at: Any) -> Job:
        if not isinstance(entry, dict):
            raise InvalidInputError(f"job #{index} must be a JSON object")
        values = {name: self._text(entry, name, index) for name in _KNOWN_FIELDS}
        for name in REQUIRED_FIELDS:
            if not values[name]:
                raise InvalidInputError(f"job #{index} is missing the required field `{name}`")
        return Job(
            id=build_job_id(
                self.name,
                external_id=values["external_id"],
                url=values["url"],
                company=values["company"],
                title=values["title"],
            ),
            source=self.name,
            title=values["title"] or "",
            company=values["company"] or "",
            description=values["description"] or "",
            url=values["url"],
            apply_email=values["apply_email"],
            raw=dict(entry),
            collected_at=collected_at,
        )

    def _text(self, entry: dict[str, Any], name: str, index: int) -> str | None:
        value = entry.get(name)
        if value is None:
            return None
        if not isinstance(value, str):
            raise InvalidInputError(f"job #{index}: `{name}` must be a string")
        stripped = value.strip()
        return stripped or None
