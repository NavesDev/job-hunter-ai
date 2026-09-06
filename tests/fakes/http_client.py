"""An in-memory `HttpClient`: the GeekHunter suites never reach the network."""

import json
import re
from hashlib import sha256
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "geekhunter"

LISTING = "https://www.geekhunter.com/pt/vagas"


def fixture(name: str) -> str:
    return FIXTURES.joinpath(name).read_text(encoding="utf-8")


class FakeHttpClient:
    """Serves recorded pages by URL and records every request, in order."""

    def __init__(self, pages: dict[str, str], failure: Exception | None = None):
        self.pages = pages
        self.failure = failure
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        if self.failure is not None:
            raise self.failure
        try:
            return self.pages[url]
        except KeyError as exc:
            raise AssertionError(f"the source requested an unrecorded page: {url}") from exc


def recorded_client(**extra_pages: str) -> FakeHttpClient:
    """The two recorded listing pages plus the detail page of every job they list."""
    pages = {
        f"{LISTING}?page=1": fixture("listing-page-1.html"),
        f"{LISTING}?page=2": fixture("listing-page-2.html"),
    }
    pages.update(detail_pages())
    pages.update(extra_pages)
    return FakeHttpClient(pages)


def detail_pages() -> dict[str, str]:
    """Maps each recorded detail page to the URL its own `JobPosting` block declares."""
    pages: dict[str, str] = {}
    for path in sorted(FIXTURES.glob("job-detail-*.html")):
        html = path.read_text(encoding="utf-8")
        match = re.search(r'type="application/ld\+json">(\{.*?\})</script>', html, re.S)
        if match is None:
            continue
        pages[json.loads(match.group(1))["url"]] = html
    return pages


def synthetic_detail(url: str) -> str:
    """A minimal detail page in the recorded shape, for jobs we did not record."""
    identifier = sha256(url.encode("utf-8")).hexdigest()
    posting = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "identifier": {"@type": "PropertyValue", "name": "GeekHunter", "value": identifier},
        "url": url,
        "title": url.rsplit("/", 1)[-1].replace("-", " ").strip(),
        "hiringOrganization": {"@type": "Organization", "name": url.split("/")[4]},
        "description": "<p>synthesized</p>",
    }
    block = json.dumps(posting, ensure_ascii=False)
    script = f'<script id="jobPosting" type="application/ld+json">{block}</script>'
    return f"<html><head>{script}</head></html>"


def client_over_both_listings() -> FakeHttpClient:
    """Both recorded listing pages, with a synthesized detail page for every job listed."""
    client = recorded_client()
    for page in ("listing-page-1.html", "listing-page-2.html"):
        for url in listed_urls(page):
            client.pages.setdefault(url, synthetic_detail(url))
    return client


def listed_urls(page: str) -> list[str]:
    """The job URLs a recorded listing page points at, in order."""
    blob = re.search(r'id="itemList"[^>]*>(\{.*?\})</script>', fixture(page), re.S)
    assert blob is not None
    return [item["url"] for item in json.loads(blob.group(1))["itemListElement"]]
