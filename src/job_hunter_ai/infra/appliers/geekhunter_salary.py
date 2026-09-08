"""Which expected salary goes into the form, out of the ones the profile predefines.

GeekHunter asks for the expectation in the contract type of the posting, and says which
one in the field's own name (`salaryExpectation.CLT`, `salaryExpectation.PJ`, ...). So the
job itself picks the right number, and `--salary` overrides that when the caller wants a
different one — always from a value the profile already declares, never a figure invented
here or typed at the prompt.
"""

from typing import Any

from job_hunter_ai.domain.errors import InvalidInputError

KEY_PREFIX = "salary_expectation"
GENERIC_KEY = KEY_PREFIX

# The contract codes GeekHunter puts on the field name, lowercased. The platform asks as
# CLT, PJ, INT (estagiário), APP (aprendiz) or TEMP (empregado temporário); only the first
# three have a kind here, because those are the ones a profile predefines. A posting asking
# as APP or TEMP raises instead of guessing which number to offer.
FIELD_SUFFIX_ALIASES: dict[str, str] = {
    "clt": "clt",
    "pj": "pj",
    "int": "internship",
    "internship": "internship",
    "estagio": "internship",
}
UNMAPPED_CONTRACTS = {"app": "aprendiz", "temp": "empregado temporário"}
KINDS = ("clt", "pj", "internship")


def configured(extra_fields: dict[str, str]) -> dict[str, str]:
    """The salary expectations the profile declares, by kind, plus the generic fallback."""
    values = {}
    for kind in KINDS:
        value = str(extra_fields.get(f"{KEY_PREFIX}_{kind}", "")).strip()
        if value:
            values[kind] = value
    generic = str(extra_fields.get(GENERIC_KEY, "")).strip()
    if generic:
        values[GENERIC_KEY] = generic
    return values


def require_any(extra_fields: dict[str, str]) -> dict[str, str]:
    """Fail before the browser opens when the profile predefines no expectation at all."""
    values = configured(extra_fields)
    if not values:
        raise InvalidInputError(
            "the geekhunter form asks for an expected salary and this profile predefines none; "
            f"add {', '.join(f'{KEY_PREFIX}_{kind}' for kind in KINDS)} to "
            "candidate.extra_fields (config/local/config.yaml)"
        )
    return values


def require_choice(values: dict[str, str], chosen: Any) -> str | None:
    """Validate `--salary` against what the profile predefines, before anything opens."""
    if chosen is None:
        return None
    kind = str(chosen).strip().lower()
    available = sorted(key for key in values if key != GENERIC_KEY)
    if kind not in KINDS:
        raise InvalidInputError(
            f"unknown --salary `{chosen}`; it picks a predefined expectation: {', '.join(KINDS)}"
        )
    if kind not in values:
        raise InvalidInputError(
            f"this profile predefines no `{KEY_PREFIX}_{kind}`; "
            f"available: {', '.join(available) or 'none'}"
        )
    return kind


def for_field(values: dict[str, str], field_name: str, chosen: str | None) -> str:
    """The value to type: the caller's choice, else the contract type the field asks for."""
    if chosen is not None:
        return values[chosen]
    kind = FIELD_SUFFIX_ALIASES.get(_suffix(field_name))
    if kind is not None and kind in values:
        return values[kind]
    if GENERIC_KEY in values:
        return values[GENERIC_KEY]
    _, _, raw_suffix = field_name.partition(".")
    suffix = raw_suffix.strip() or field_name
    described = UNMAPPED_CONTRACTS.get(suffix.lower(), suffix)
    available = ", ".join(sorted(key for key in values if key != GENERIC_KEY))
    raise InvalidInputError(
        f"this posting asks for the expected salary as `{suffix}` ({described}) and the "
        f"profile predefines no amount for it; add `{GENERIC_KEY}` to candidate.extra_fields "
        f"as a fallback, or pass --salary with one of: {available}"
    )


def _suffix(field_name: str) -> str:
    _, _, suffix = field_name.partition(".")
    return suffix.strip().lower()
