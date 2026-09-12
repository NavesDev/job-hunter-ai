"""Translates domain entities into the JSON payloads declared in docs/CONTRACT.md."""

from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult
from job_hunter_ai.domain.entities.ats_score import AtsScore, Knockout, SkillMatch
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.session_result import SessionResult
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


def session_result_to_payload(result: SessionResult) -> dict[str, Any]:
    """The `login` contract: what the session is, and where the profile holding it lives."""
    return {
        "source": result.source,
        "status": str(result.status),
        "profile_dir": result.profile_dir,
        "detail": result.detail,
        "checked_at": to_iso_utc(result.checked_at) if result.checked_at else None,
    }


def ats_score_to_payload(score: AtsScore) -> dict[str, Any]:
    """An `AtsScore` as the contract's score-job object, rationale included."""
    return {
        "job_id": score.job_id,
        "source": score.source,
        "title": score.title,
        "company": score.company,
        "score": score.score,
        "verdict": str(score.verdict),
        "components": dict(score.components),
        "required_skills": _skill_match_to_payload(score.required_skills),
        "preferred_skills": _skill_match_to_payload(score.preferred_skills),
        "experience": {
            "required_months": score.experience.required_months,
            "detected_months": score.experience.detected_months,
            "meets": score.experience.meets,
        },
        "knockouts": [_knockout_to_payload(knockout) for knockout in score.knockouts],
        "resume_path": str(score.resume_path),
        "scored_at": to_iso_utc(score.scored_at) if score.scored_at else None,
    }


def _skill_match_to_payload(match: SkillMatch) -> dict[str, Any]:
    return {"matched": list(match.matched), "missing": list(match.missing)}


def _knockout_to_payload(knockout: Knockout) -> dict[str, Any]:
    return {"rule": knockout.rule, "passed": knockout.passed, "detail": knockout.detail}
