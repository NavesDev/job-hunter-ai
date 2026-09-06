"""The listing filters, and the only values GeekHunter actually honors.

The platform ignores an unknown filter value silently: `workModality=in_person`
returns the *unfiltered* listing, not an error. Handing that back would be a lie, so
every value is checked against what was verified against the live site before any
request goes out (docs/superpowers/specs/2026-09-05-geekhunter-source-design.md).
"""

from datetime import datetime
from typing import Any

from job_hunter_ai.domain.errors import InvalidInputError

ENUMERATED_FILTERS: dict[str, frozenset[str]] = {
    "workModality": frozenset({"remote", "hybrid", "on-site", "remote-in-city"}),
    "experienceLevel": frozenset({"intern", "entry", "mid", "senior", "manager"}),
}
TEXT_FILTERS = frozenset({"searchTerm", "cityName"})
INTEGER_FILTERS = frozenset({"minSalary", "maxSalary"})
INSTANT_FILTERS = frozenset({"publishedAfter"})

KNOWN_FILTERS = frozenset(ENUMERATED_FILTERS) | TEXT_FILTERS | INTEGER_FILTERS | INSTANT_FILTERS


def validated(filters: Any) -> dict[str, str]:
    """Return the filters as query parameters, raising on anything unverified."""
    if filters is None:
        return {}
    if not isinstance(filters, dict):
        raise InvalidInputError("`filters` must be a mapping of filter name to value")
    return {name: _value(name, value) for name, value in sorted(filters.items())}


def _value(name: str, value: Any) -> str:
    if name not in KNOWN_FILTERS:
        known = ", ".join(sorted(KNOWN_FILTERS))
        raise InvalidInputError(f"unknown geekhunter filter `{name}`; known filters: {known}")
    text = str(value).strip()
    if not text:
        raise InvalidInputError(f"geekhunter filter `{name}` has an empty value")
    if name in ENUMERATED_FILTERS:
        return _enumerated(name, text)
    if name in INTEGER_FILTERS:
        return _integer(name, text)
    if name in INSTANT_FILTERS:
        return _instant(name, text)
    return text


def _enumerated(name: str, text: str) -> str:
    allowed = ENUMERATED_FILTERS[name]
    if text not in allowed:
        raise InvalidInputError(
            f"unknown value `{text}` for the geekhunter filter `{name}`; "
            f"allowed: {', '.join(sorted(allowed))}"
        )
    return text


def _integer(name: str, text: str) -> str:
    try:
        return str(int(text))
    except ValueError as exc:
        raise InvalidInputError(
            f"the geekhunter filter `{name}` takes a whole number, got `{text}`"
        ) from exc


def _instant(name: str, text: str) -> str:
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidInputError(
            f"the geekhunter filter `{name}` takes an ISO 8601 instant, got `{text}`"
        ) from exc
    return text
