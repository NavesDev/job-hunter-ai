"""Finds the candidate's contact details the way a résumé parser does: by shape.

A parser never looks for the word "e-mail" — it looks for something shaped like an
address or a phone number, and lifts it into its own field. A résumé that prints
`davi@example.com | (61) 90000-0000` is perfectly reachable, and scoring it as if it had
no contact section would be an artifact of the checker, not a fact about the file.
"""

import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# A run of digits and separators; the digit count is what tells a phone from a year range.
PHONE = re.compile(r"(?:\+\d{1,3}[\s.\-]*)?(?:\(\d{2,4}\)[\s.\-]*)?\d[\d\s.\-]{7,14}\d")
MIN_PHONE_DIGITS = 10


def has_email(text: str) -> bool:
    return EMAIL.search(text) is not None


def has_phone(text: str) -> bool:
    """`2018 - 2021` is a date range, not a number anyone can call: hence the digit count."""
    return any(
        len(re.sub(r"\D", "", candidate.group())) >= MIN_PHONE_DIGITS
        for candidate in PHONE.finditer(text)
    )


def is_reachable(text: str) -> bool:
    """Whether the résumé carries at least one way of reaching the candidate."""
    return has_email(text) or has_phone(text)
