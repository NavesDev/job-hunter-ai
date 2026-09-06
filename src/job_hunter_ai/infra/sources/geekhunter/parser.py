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
