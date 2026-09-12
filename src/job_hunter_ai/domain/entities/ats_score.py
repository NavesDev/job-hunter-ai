from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class ScoreVerdict(StrEnum):
    """How an ATS would rank the résumé for the job. See docs/CONTRACT.md."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    POOR = "poor"
    KNOCKOUT = "knockout"


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """The requirements the résumé answers, and the ones it does not."""

    matched: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExperienceMatch:
    """Months of experience the posting asks for against the months read off the résumé."""

    required_months: int | None
    detected_months: int
    meets: bool


@dataclass(frozen=True, slots=True)
class Knockout:
    """A hard filter an ATS applies before ranking anything."""

    rule: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class AtsScore:
    """The full rationale of one resume-versus-job comparison, never just the number."""

    job_id: str
    source: str
    title: str
    company: str
    score: float
    verdict: ScoreVerdict
    resume_path: Path
    components: Mapping[str, float] = field(default_factory=dict)
    required_skills: SkillMatch = field(default_factory=SkillMatch)
    preferred_skills: SkillMatch = field(default_factory=SkillMatch)
    experience: ExperienceMatch = field(default_factory=lambda: ExperienceMatch(None, 0, True))
    knockouts: tuple[Knockout, ...] = ()
    scored_at: datetime | None = None
