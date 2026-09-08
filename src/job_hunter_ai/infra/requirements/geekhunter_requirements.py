"""Reads a GeekHunter posting the way its own form fills it in.

The platform publishes the must-haves twice: as the `skills` string of the `JobPosting`
and as the `Requisitos` list at the top of the description. The nice-to-haves only ever
appear in the description, under a heading of their own — hence the two paths here.
"""

from typing import Any

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.job_requirements import JobRequirements
from job_hunter_ai.domain.matching.normalizer import normalize
from job_hunter_ai.infra.requirements import html_text
from job_hunter_ai.infra.requirements.terms import clean_terms

REQUIRED_HEADINGS = ("requisito",)
PREFERRED_HEADINGS = ("desejav", "diferenc", "nice to have", "plus")
STOP_HEADINGS = ("tarefa", "responsabilidade", "sobre", "benefic", "competencia", "atividade")


class GeekHunterRequirementsExtractor:
    """The `RequirementsExtractor` port for the `geekhunter` source."""

    name = "geekhunter"

    def extract(self, job: Job) -> JobRequirements:
        sections = _sections(job.description)
        preferred = clean_terms(*sections.get("preferred", ()))
        required = clean_terms(_skills(job.raw), *sections.get("required", ()))
        return JobRequirements(
            title=str(job.raw.get("title") or job.title),
            required=_without(required, preferred),
            preferred=preferred,
            months_of_experience=_months(job.raw),
        )


def _skills(raw: dict[str, Any]) -> list[str]:
    """The `skills` field is a single comma-joined string, not a list."""
    return str(raw.get("skills") or "").split(",")


def _months(raw: dict[str, Any]) -> int | None:
    requirement = raw.get("experienceRequirements")
    if not isinstance(requirement, dict):
        return None
    months = requirement.get("monthsOfExperience")
    return int(months) if isinstance(months, int | float | str) and str(months).isdigit() else None


def _sections(description: str) -> dict[str, list[str]]:
    """Split the description's lists into the required and the preferred buckets."""
    found: dict[str, list[str]] = {"required": [], "preferred": []}
    bucket: str | None = None
    for is_heading, text in html_text.blocks(description):
        if is_heading:
            bucket = _bucket_of(text)
        elif bucket is not None:
            found[bucket].append(text)
    return found


def _without(terms: tuple[str, ...], excluded: tuple[str, ...]) -> tuple[str, ...]:
    """The `skills` field repeats the nice-to-haves; the description is what tells them apart."""
    dropped = {normalize(term) for term in excluded}
    return tuple(term for term in terms if normalize(term) not in dropped)


def _bucket_of(heading: str) -> str | None:
    lowered = normalize(heading)
    if any(word in lowered for word in PREFERRED_HEADINGS):
        return "preferred"
    if any(word in lowered for word in REQUIRED_HEADINGS):
        return "required"
    if any(word in lowered for word in STOP_HEADINGS):
        return None
    return None
