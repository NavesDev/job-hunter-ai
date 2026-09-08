"""What the browser saw when an application did not end in GeekHunter's confirmation.

An attempt that stops without `Candidatura Completa` is the outcome the caller can act on
least and needs most: the form may have been refused, or taken and answered with screening
questions. So the page itself is the evidence — quoted in the error and kept on disk, with
the candidate's own values taken out of the quote.

Nothing here may raise. A diagnostic that fails is a diagnostic missing, never a failure
replacing the one being reported.
"""

from pathlib import Path
from typing import Any

from job_hunter_ai.domain.time_utils import utc_now

SNIPPET_LIMIT = 320


def unconfirmed(page: Any, url: str, values: dict[str, str], diagnostics_dir: Path) -> str:
    """Say what the platform answered instead, so the next run is not blind.

    `Candidatura Completa` missing means one of two very different things — the form
    was refused, or it went through and said so differently — and the message alone
    could never tell them apart. What the page became is the evidence, so it is
    quoted here and kept on disk.
    """
    return " ".join(
        part
        for part in (
            f"geekhunter never confirmed the application for {url};",
            "the attempt may or may not have gone through.",
            what_the_page_said(page, values),
            saved_page(page, url, diagnostics_dir),
        )
        if part
    )


def screening(page: Any, url: str, diagnostics_dir: Path) -> str:
    """Hand the questions back: only the candidate knows their own answers."""
    questions = questions_on(page)
    asked = " ".join(f"`{question}`" for question in questions) if questions else ""
    return " ".join(
        part
        for part in (
            f"geekhunter took the form for {url} and is asking screening questions"
            " before the application counts;",
            f"it asks {asked}." if asked else "it does not say which on the page.",
            "answer them with `--answer <question-id>=<value>` — nothing here"
            " answers for you, and nothing else was sent.",
            saved_page(page, url, diagnostics_dir),
        )
        if part
    )


def what_the_page_said(page: Any, values: dict[str, str]) -> str:
    """The visible text the page ended on, with the candidate's own values taken out."""
    try:
        text = " ".join(str(page.locator("body").first.inner_text()).split())
        where = str(page.url)
    except Exception:
        return ""  # a page that cannot even be read must not mask the original failure
    for value in values.values():
        if value:
            text = text.replace(value, "…")
    if not text:
        return f"it ended on {where}, with no visible text."
    return f"it ended on {where}, saying `{_both_ends(text)}`."


def saved_page(page: Any, url: str, diagnostics_dir: Path) -> str:
    """Keep the page itself next to the message: a snippet is rarely the whole story."""
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    target = diagnostics_dir / f"unconfirmed-{stamp}.html"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"<!-- {url} -->\n{page.content()}", encoding="utf-8")
    except Exception:
        return ""  # diagnostics are a courtesy; failing to write one changes nothing
    return f"the page as it was is in {target}."


# --- the outcome ---


def is_showing(locator: Any) -> bool:
    """Whether the element is on the page right now, without waiting for it to appear."""
    try:
        return bool(locator.count()) and bool(locator.is_visible())
    except Exception:
        return False  # a page mid-navigation answers nothing; the next poll asks again


def questions_on(page: Any) -> list[str]:
    """The screening questions as the page words them, in the order it asks them."""
    try:
        text = str(page.locator("body").first.inner_text())
    except Exception:
        return []
    asked = [" ".join(line.split()) for line in text.splitlines() if line.strip().endswith("?")]
    return list(dict.fromkeys(asked))


def _both_ends(text: str) -> str:
    """Keep the start and the end of the page text: the answer sits at one of them.

    A page that replaced itself says what happened up top; a page that only appended a
    message under the form it kept says it at the very bottom. Quoting one end alone
    would lose that answer half the time.
    """
    if len(text) <= SNIPPET_LIMIT:
        return text
    half = SNIPPET_LIMIT // 2
    return f"{text[:half]} […] {text[-half:]}"
