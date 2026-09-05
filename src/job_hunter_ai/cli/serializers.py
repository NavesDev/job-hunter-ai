"""Translates domain entities into the JSON payloads declared in docs/CONTRACT.md."""

from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.time_utils import to_iso_utc


def job_to_payload(job: Job) -> dict[str, Any]:
    """A `Job` as the contract's list-jobs item, with dates in ISO 8601 UTC."""
    return {
        "id": job.id,
        "source": job.source,
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "url": job.url,
        "apply_email": job.apply_email,
        "raw": job.raw,
        "collected_at": to_iso_utc(job.collected_at) if job.collected_at else None,
    }


def application_result_to_payload(result: ApplicationResult) -> dict[str, Any]:
    """An `ApplicationResult` as the contract's apply-job object."""
    return {
        "job_id": result.job_id,
        "method": result.method,
        "status": str(result.status),
        "applier": result.applier,
        "detail": result.detail,
        "applied_at": to_iso_utc(result.applied_at) if result.applied_at else None,
    }
