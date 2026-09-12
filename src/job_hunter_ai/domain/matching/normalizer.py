"""Deterministic text normalization: the only way a term is ever compared.

Accents, casing and punctuation are noise for a keyword matcher — a résumé written
`Experiência` must match a posting written `experiencia`.
"""

import re
import unicodedata

from job_hunter_ai.domain.matching.aliases import canonical

# `+`, `#` and `.` survive because they carry meaning in a skill name: C#, C++, .NET.
_NOISE = re.compile(r"[^a-z0-9+#.]+")


def normalize(text: str) -> str:
    """Casefold, strip accents and collapse every other separator into a single space."""
    folded = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return _NOISE.sub(" ", plain).strip()


def tokens(text: str) -> tuple[str, ...]:
    """The canonical tokens of a text, aliases already resolved."""
    return tuple(canonical(word) for word in normalize(text).split() if word.strip("."))


def canonical_text(text: str) -> str:
    """The text as a single canonical token stream, ready to be searched for phrases."""
    return " ".join(tokens(text))


def mentions(haystack: str, term: str) -> bool:
    """Whether an already canonical haystack contains `term` as a whole phrase.

    Whole phrase, not substring: `React` must not match `Reactive`, and a two-word skill
    such as `Casos de Teste` only counts when its words appear together.
    """
    needle = canonical_text(term)
    if not needle:
        return False
    return f" {needle} " in f" {haystack} "
