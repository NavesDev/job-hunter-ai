"""The synonyms a screening robot is expected to know.

An ATS does not read: it compares strings. What keeps it from missing `JS` on a résumé
that says `JavaScript` is a table exactly like this one — explicit, versioned and small.
Anything not listed here has to match literally, which is also what happens in the real
systems (docs/scoring.md#aliases).
"""

from collections.abc import Mapping

ALIASES: Mapping[str, str] = {
    ".net": "dotnet",
    "angularjs": "angular",
    "c#": "csharp",
    "gcp": "googlecloud",
    "golang": "go",
    "js": "javascript",
    "k8s": "kubernetes",
    "mongo": "mongodb",
    "next.js": "nextjs",
    "node": "nodejs",
    "node.js": "nodejs",
    "postgres": "postgresql",
    "psql": "postgresql",
    "py": "python",
    "reactjs": "react",
    "restful": "rest",
    "ts": "typescript",
    "vue.js": "vue",
    "vuejs": "vue",
}

MIN_PLURAL_LENGTH = 3
# Endings where a final `s` is part of the word, not a plural: `nodejs`, `access`, `status`.
PLURAL_EXCEPTIONS = ("ss", "us", "js")


def canonical(token: str) -> str:
    """The single spelling a token is compared under, on both sides of the match.

    The plural is folded away after the alias so that `APIs` and `API` are the same term.
    Being applied to the posting and to the résumé alike, the rule can only make both
    sides agree — never one of them wrong.
    """
    alias = ALIASES.get(token) or ALIASES.get(token.strip("."), token.strip(".")) or token
    if (
        len(alias) > MIN_PLURAL_LENGTH
        and alias.endswith("s")
        and not alias.endswith(PLURAL_EXCEPTIONS)
    ):
        return alias[:-1]
    return alias
