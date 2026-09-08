"""The scoring model: how a screening robot would rank one résumé for one job.

Deterministic by construction — same résumé and same posting, same number, always. The
weights below reproduce the public consensus on how the big platforms rank: required
keywords dominate, knockouts reject regardless of the score, and a file the parser cannot
read loses points no matter what it says. Every number is justified in docs/scoring.md.
"""

from collections.abc import Iterable, Mapping

from job_hunter_ai.domain.entities.ats_score import (
    AtsScore,
    ExperienceMatch,
    Knockout,
    ScoreVerdict,
    SkillMatch,
)
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.job_requirements import JobRequirements
from job_hunter_ai.domain.entities.resume_document import ResumeDocument
from job_hunter_ai.domain.matching import experience
from job_hunter_ai.domain.matching.normalizer import canonical_text, mentions, tokens
from job_hunter_ai.domain.time_utils import utc_now

WEIGHTS: Mapping[str, float] = {
    "required_skills": 45.0,
    "preferred_skills": 10.0,
    "title_alignment": 10.0,
    "experience": 20.0,
    "parseability": 10.0,
    "sections": 5.0,
}

STRONG_SCORE = 80.0
MODERATE_SCORE = 60.0
WEAK_SCORE = 40.0

# A page of an ordinary résumé yields well over this; a scanned or image-only page yields
# almost nothing. The ratio is the closest a text parser gets to "is this file readable".
CHARS_PER_READABLE_PAGE = 700

SECTIONS: Mapping[str, tuple[str, ...]] = {
    "contact": ("email", "e mail", "telefone", "phone", "linkedin", "contato", "contact"),
    "experience": ("experiencia", "experience", "profissional", "employment"),
    "education": ("formacao", "educacao", "education", "academic", "escolaridade"),
    "skills": ("habilidades", "competencias", "skills", "tecnologias", "conhecimentos"),
    "summary": ("resumo", "objetivo", "sobre mim", "summary", "profile", "perfil"),
}

# Words a job title shares with every other job title: matching them proves nothing.
TITLE_STOPWORDS = frozenset({"de", "da", "do", "e", "em", "para", "of", "and", "the", "com"})


class AtsScorer:
    """Scores a résumé against a job's requirements. Pure: no I/O, no clock beyond `scored_at`."""

    def score(self, job: Job, requirements: JobRequirements, resume: ResumeDocument) -> AtsScore:
        text = canonical_text(resume.text)
        required = self._match(requirements.required, text)
        preferred = self._match(requirements.preferred, text)
        months = experience.total_months(resume.text)
        seniority = self._experience(requirements.months_of_experience, months)
        components = {
            "required_skills": self._ratio(required),
            "preferred_skills": self._ratio(preferred),
            "title_alignment": self._title_alignment(requirements.title or job.title, text),
            "experience": self._experience_score(seniority),
            "parseability": self._parseability(resume),
            "sections": self._sections(text),
        }
        knockouts = self._knockouts(seniority)
        total = sum(components[name] * weight for name, weight in WEIGHTS.items()) / 100
        return AtsScore(
            job_id=job.id,
            source=job.source,
            title=job.title,
            company=job.company,
            score=round(total, 1),
            verdict=self._verdict(total, knockouts),
            resume_path=resume.path,
            components={name: round(value, 1) for name, value in components.items()},
            required_skills=required,
            preferred_skills=preferred,
            experience=seniority,
            knockouts=knockouts,
            scored_at=utc_now(),
        )

    def _match(self, terms: Iterable[str], text: str) -> SkillMatch:
        wanted = tuple(terms)
        matched = tuple(term for term in wanted if mentions(text, term))
        return SkillMatch(matched=matched, missing=tuple(t for t in wanted if t not in matched))

    def _ratio(self, match: SkillMatch) -> float:
        """Nothing asked for is nothing missing: an empty requirement never costs points."""
        total = len(match.matched) + len(match.missing)
        return 100.0 if total == 0 else 100.0 * len(match.matched) / total

    def _title_alignment(self, title: str, text: str) -> float:
        words = tuple(word for word in tokens(title) if word not in TITLE_STOPWORDS)
        if not words:
            return 100.0
        present = sum(1 for word in words if mentions(text, word))
        return 100.0 * present / len(words)

    def _experience(self, required_months: int | None, detected: int) -> ExperienceMatch:
        meets = required_months is None or detected >= required_months
        return ExperienceMatch(
            required_months=required_months, detected_months=detected, meets=meets
        )

    def _experience_score(self, match: ExperienceMatch) -> float:
        if not match.required_months:
            return 100.0
        return min(100.0, 100.0 * match.detected_months / match.required_months)

    def _parseability(self, resume: ResumeDocument) -> float:
        pages = max(resume.pages, 1)
        density = len(resume.text.strip()) / (pages * CHARS_PER_READABLE_PAGE)
        return min(100.0, 100.0 * density)

    def _sections(self, text: str) -> float:
        found = sum(1 for terms in SECTIONS.values() if any(mentions(text, t) for t in terms))
        return 100.0 * found / len(SECTIONS)

    def _knockouts(self, seniority: ExperienceMatch) -> tuple[Knockout, ...]:
        if seniority.required_months is None:
            return ()
        return (
            Knockout(
                rule="min_experience",
                passed=seniority.meets,
                detail=(
                    f"{seniority.required_months} months required, "
                    f"{seniority.detected_months} detected"
                ),
            ),
        )

    def _verdict(self, total: float, knockouts: tuple[Knockout, ...]) -> ScoreVerdict:
        """A failed hard filter outranks the number, the way it does in a real ATS."""
        if any(not knockout.passed for knockout in knockouts):
            return ScoreVerdict.KNOCKOUT
        if total >= STRONG_SCORE:
            return ScoreVerdict.STRONG
        if total >= MODERATE_SCORE:
            return ScoreVerdict.MODERATE
        if total >= WEAK_SCORE:
            return ScoreVerdict.WEAK
        return ScoreVerdict.POOR
