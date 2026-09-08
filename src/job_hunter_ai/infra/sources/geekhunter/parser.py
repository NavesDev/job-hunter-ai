"""Reads the `application/ld+json` blocks GeekHunter renders on every page.

The platform ships schema.org data server-side: an `ItemList` on the listing and a
`JobPosting` on each job page. Parsing those blocks — instead of the visual markup —
is what keeps this source independent of a CSS class rename.
"""

import json
from html.parser import HTMLParser
from typing import Any

from job_hunter_ai.domain.errors import SourceError

LD_JSON = "application/ld+json"
SCREENING_KEY = "screeningQuestions"


class _LdJsonCollector(HTMLParser):
    """Collects the raw text of every `<script type="application/ld+json">`."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._inside = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type") == LD_JSON:
            self._inside = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self.blocks.append(data)


def _documents(html: str) -> list[dict[str, Any]]:
    collector = _LdJsonCollector()
    collector.feed(html)
    documents = []
    for block in collector.blocks:
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue  # a malformed block is not ours to fix; the caller fails on the missing type
        if isinstance(parsed, dict):
            documents.append(parsed)
    return documents


def _of_type(html: str, expected: str, url: str) -> dict[str, Any]:
    for document in _documents(html):
        if document.get("@type") == expected:
            return document
    raise SourceError(f"no `{expected}` structured data in {url}; the page changed shape")


def listing_job_urls(html: str, url: str) -> list[str]:
    """The job URLs the listing page points at, in the order the platform ranked them."""
    item_list = _of_type(html, "ItemList", url)
    elements = item_list.get("itemListElement")
    if not isinstance(elements, list):
        raise SourceError(f"the ItemList in {url} carries no `itemListElement`")
    urls = [item["url"] for item in elements if isinstance(item, dict) and item.get("url")]
    if not urls:
        raise SourceError(f"the listing at {url} returned no job")
    return urls


def job_posting(html: str, url: str) -> dict[str, Any]:
    """The `JobPosting` payload of a job detail page, untouched."""
    return _of_type(html, "JobPosting", url)


def screening_questions(html: str) -> list[dict[str, Any]]:
    """The questions the job asks after the form, in the platform's own shape.

    These are the one thing the `JobPosting` block omits: they live in the page's app
    payload, JSON escaped inside a script. Reading them here is what lets `apply-job`
    check an answer against the question it belongs to before opening a browser — the
    alternative is discovering a mandatory question with the form already submitted.
    """
    for marker, escaped in ((f'\\"{SCREENING_KEY}\\":', True), (f'"{SCREENING_KEY}":', False)):
        start = html.find(marker)
        if start == -1:
            continue
        blob = _array_at(html, start + len(marker))
        if blob is None:
            continue
        questions = _loaded(blob, escaped)
        if questions is not None:
            return questions
    return []


def _array_at(html: str, index: int) -> str | None:
    """The `[...]` starting at `index`, brackets balanced. `null` and anything else: none."""
    while index < len(html) and html[index] in " \\n":
        index += 1
    if index >= len(html) or html[index] != "[":
        return None
    depth = 0
    for position in range(index, len(html)):
        if html[position] == "[":
            depth += 1
        elif html[position] == "]":
            depth -= 1
            if depth == 0:
                return html[index : position + 1]
    return None


def _loaded(blob: str, escaped: bool) -> list[dict[str, Any]] | None:
    """Decode the array, unescaping it first when it sits inside a JavaScript string."""
    try:
        text = json.loads(f'"{blob}"') if escaped else blob
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None  # a payload we cannot read is not a payload we may guess at
    if not isinstance(parsed, list):
        return None
    return [item for item in parsed if isinstance(item, dict)]
