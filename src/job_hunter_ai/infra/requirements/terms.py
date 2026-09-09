"""Cleans the raw strings a posting lists into terms worth matching.

Postings do not write skills, they write sentences around them: "Conhecimento em Java 8 ou
superior", "Docker e Kubernetes", "5+ anos de experiência". What a keyword matcher needs is
the skill, so the filler around it is trimmed, the years line is dropped (it is the
seniority requirement, scored on its own) and anything too long to be a keyword is left out.
"""

import re

from job_hunter_ai.domain.matching.normalizer import normalize

MAX_TERM_WORDS = 6
# Words that only ever wrap a skill: dropping them from the edges leaves the skill itself.
QUALIFIERS = frozenset(
    {
        "a", "acima", "above", "com", "conhecimento", "conhecimentos", "da", "de", "desejavel",
        "do", "e", "em", "experiencia", "experiencias", "higher", "in", "knowledge", "minimo",
        "of", "ou", "or", "solida", "solido", "superior", "using", "vivencia", "with",
    }
)  # fmt: skip
_YEARS = re.compile(r"\b\d+\s*\+?\s*(?:anos?|years?)\b", re.IGNORECASE)
_CONTACT = re.compile(r"[@]|https?://")
_VERSION = re.compile(r"^\d+(?:\.\d+)*\+?$")


def clean_terms(*groups: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Flatten, trim and de-duplicate the terms of a posting, keeping the reading order."""
    seen: dict[str, str] = {}
    for group in groups:
        for raw in [group] if isinstance(group, str) else group:
            for term in _split(raw):
                if not _is_term(term):
                    continue
                trimmed = _trim(term)
                if trimmed:
                    seen.setdefault(normalize(trimmed), trimmed)
    return tuple(seen.values())


def _split(raw: str) -> list[str]:
    """A leading dot is never punctuation here: `.NET` is the skill's own name."""
    parts = re.split(r"[,;•\n]|(?: e/ou )|(?: e )", raw)
    return [part.strip(" ;:•-/").rstrip(".").strip() for part in parts]


def _trim(term: str) -> str:
    """Drop the filler and the version number around a skill: `Java 8 ou superior` is Java."""
    words = term.split()
    while words and _is_filler(words[0]):
        words.pop(0)
    while words and _is_filler(words[-1]):
        words.pop()
    return " ".join(words)


def _is_filler(word: str) -> bool:
    plain = normalize(word)
    return not plain or plain in QUALIFIERS or bool(_VERSION.match(plain))


def _is_term(term: str) -> bool:
    """Checked before trimming: `2+ anos` only reads as a years line while it keeps its number."""
    if not term or len(term.split()) > MAX_TERM_WORDS:
        return False
    return not _YEARS.search(term) and not _CONTACT.search(term)
