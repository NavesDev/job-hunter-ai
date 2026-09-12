"""Months of professional experience, read off the résumé the way an ATS reads them.

The number never comes from a sentence like "8 years of experience" — that is a claim,
not a fact a parser can check. It comes from the date ranges of the positions, merged so
that two overlapping jobs are not counted twice (docs/scoring.md#experience).

Only the experience section is read: a degree that ran from 2022 to 2024 is not four
years of work, and counting it would inflate every junior résumé.
"""

import re
import unicodedata
from datetime import date

MONTHS = {
    "jan": 1, "fev": 2, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "mai": 5, "may": 5,
    "jun": 6, "jul": 7, "ago": 8, "aug": 8, "set": 9, "sep": 9, "out": 10, "oct": 10,
    "nov": 11, "dez": 12, "dec": 12,
}  # fmt: skip
ONGOING = ("atual", "presente", "present", "current", "hoje", "today", "now", "momento")

_NAMES = "|".join(MONTHS)
_SEPARATOR = r"[/\-.\s]+(?:de\s+)?"
_RANGE_SEPARATOR = r"\s*(?:-{1,2}|\u2013|\u2014|ate|to|until|a)\s*"


def _point(prefix: str) -> str:
    return (
        rf"(?:(?P<{prefix}month>\d{{1,2}}|{_NAMES})[a-z]*{_SEPARATOR})?"
        rf"(?P<{prefix}year>(?:19|20)\d{{2}})"
    )


_RANGE = re.compile(
    _point("start") + _RANGE_SEPARATOR + rf"(?:{_point('end')}|(?P<ongoing>{'|'.join(ONGOING)}))"
)
# A position with a start and no end: "desde 12/2025", "since Jan 2024".
_OPEN_RANGE = re.compile(rf"(?:desde|since)\s+{_point('open')}")

# Headings are matched on the text with its whitespace collapsed: a PDF parser breaks
# lines wherever it likes, so a line-based rule would miss most résumés.
# Two tiers, tried in order: the unambiguous headings first, because the bare word
# "experiência" also shows up in prose ("experiência real em produção") and would cut
# the section open in the wrong place.
EXPERIENCE_HEADINGS = (
    (
        "experiencia profissional",
        "experiencias profissionais",
        "professional experience",
        "work experience",
        "employment history",
        "historico profissional",
    ),
    ("experiencia", "experience"),
)
# Only headings that are unlikely to show up in a sentence: "projetos" or "cursos" would
# cut the section in the middle of a bullet describing a position.
NEXT_HEADINGS = (
    "formacao academica",
    "educacao",
    "education",
    "escolaridade",
    "habilidades",
    "competencias",
    "hard skills",
    "soft skills",
    "certificac",
    "idiomas",
    "languages",
    "voluntariado",
    "publicacoes",
)


def total_months(text: str, today: date | None = None) -> int:
    """Sum of the résumé's date ranges, overlaps counted once and futures clipped to today."""
    now = today or date.today()
    ceiling = now.year * 12 + now.month
    intervals = sorted(_intervals(_experience_section(_plain(text)), ceiling))
    total = 0
    covered_until = -1
    for start, end in intervals:
        if end <= covered_until:
            continue
        total += end - max(start, covered_until + 1) + 1
        covered_until = end
    return total


def _experience_section(text: str) -> str:
    """The slice of the résumé that lists positions, or the whole text when it names none."""
    collapsed = " ".join(text.split())
    begin = -1
    for tier in EXPERIENCE_HEADINGS:
        found = [collapsed.find(heading) for heading in tier]
        begin = min((start for start in found if start >= 0), default=-1)
        if begin >= 0:
            break
    if begin < 0:
        return collapsed
    ends = [collapsed.find(heading, begin + 1) for heading in NEXT_HEADINGS]
    end = min((stop for stop in ends if stop >= 0), default=len(collapsed))
    return collapsed[begin:end]


def _intervals(text: str, ceiling: int) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for match in _OPEN_RANGE.finditer(text):
        start = _index(match.group("openmonth"), match.group("openyear"), default_month=1)
        if start <= ceiling:
            found.append((start, ceiling))
    for match in _RANGE.finditer(text):
        start = _index(match.group("startmonth"), match.group("startyear"), default_month=1)
        end = (
            ceiling
            if match.group("ongoing")
            else _index(match.group("endmonth"), match.group("endyear"), default_month=12)
        )
        end = min(end, ceiling)
        if start <= end:
            found.append((start, end))
    return found


def _index(month: str | None, year: str, default_month: int) -> int:
    """A year/month pair as a single month number, so intervals are plain integers."""
    return int(year) * 12 + _month_number(month, default_month)


def _month_number(month: str | None, default: int) -> int:
    if month is None:
        return default
    if month.isdigit():
        return min(max(int(month), 1), 12)
    return MONTHS[month[:3]]


def _plain(text: str) -> str:
    """Casefolded and accent-free, but with the punctuation dates are written with."""
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))
