"""The `geekhunter` source: collects jobs from the platform's public listing."""

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import SourceError
from job_hunter_ai.domain.job_id import build_job_id
from job_hunter_ai.domain.time_utils import utc_now
from job_hunter_ai.infra.sources.geekhunter import parser
from job_hunter_ai.infra.sources.geekhunter.filters import validated
from job_hunter_ai.infra.sources.geekhunter.http_client import HttpClient

DEFAULT_BASE_URL = "https://www.geekhunter.com"
LISTING_PATH = "/pt/vagas"
MAX_LISTING_PAGES = 83


class GeekHunterJobSource:
    """Walks the public listing and normalizes each job's `JobPosting` payload.

    One listing page carries ten job URLs and no job data, so collecting `n` jobs
    costs `ceil(n / 10)` listing requests plus `n` detail requests — the pacing lives
    in the injected `HttpClient`, not here.
    """

    name = "geekhunter"

    def __init__(self, http_client: HttpClient, settings: dict[str, Any] | None = None) -> None:
        self._http = http_client
        settings = settings or {}
        self._base_url = str(settings.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
        self._filters = validated(settings.get("filters"))

    def fetch(self, max_length: int, **options: Any) -> list[Job]:
        urls = self._job_urls(max_length)
        collected_at = utc_now()
        return [self._job(url, collected_at) for url in urls]

    def _job_urls(self, max_length: int) -> list[str]:
        urls: list[str] = []
        for page in range(1, MAX_LISTING_PAGES + 1):
            listing_url = self._listing_url(page)
            found = parser.listing_job_urls(self._http.get(listing_url), listing_url)
            urls.extend(url for url in found if url not in urls)
            if len(urls) >= max_length:
                break
        return urls[:max_length]

    def _listing_url(self, page: int) -> str:
        query = urlencode({"page": page, **self._filters})
        return f"{self._base_url}{LISTING_PATH}?{query}"

    def _job(self, url: str, collected_at: datetime) -> Job:
        posting = parser.job_posting(self._http.get(url), url)
        external_id = self._external_id(posting, url)
        title = self._text(posting.get("title"))
        company = self._text(self._organization(posting).get("name"))
        if not title or not company:
            raise SourceError(f"the JobPosting in {url} has no title or no company")
        return Job(
            id=build_job_id(
                self.name, external_id=external_id, url=url, company=company, title=title
            ),
            source=self.name,
            title=title,
            company=company,
            description=self._text(posting.get("description")),
            url=self._text(posting.get("url")) or url,
            apply_email=None,  # the platform exposes no address: applying goes through its form
            raw=posting,
            collected_at=collected_at,
        )

    def _external_id(self, posting: dict[str, Any], url: str) -> str | None:
        identifier = posting.get("identifier")
        if not isinstance(identifier, dict):
            raise SourceError(f"the JobPosting in {url} carries no identifier")
        return self._text(identifier.get("value")) or None

    def _organization(self, posting: dict[str, Any]) -> dict[str, Any]:
        organization = posting.get("hiringOrganization")
        return organization if isinstance(organization, dict) else {}

    def _text(self, value: Any) -> str:
        return value.strip() if isinstance(value, str) else ""
