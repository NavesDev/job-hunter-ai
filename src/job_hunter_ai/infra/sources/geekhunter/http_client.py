"""The one place this project talks HTTP, kept behind a seam the tests replace.

Two things are not negotiable here. GeekHunter sits behind a CDN that answers `403`
to the standard library's default user-agent, so the client always identifies itself;
and the tool applies for one candidate, not a crawl, so requests are paced.
"""

import time
import urllib.error
import urllib.request
from typing import Protocol

from job_hunter_ai.domain.errors import SourceError

DEFAULT_USER_AGENT = "job-hunter-ai/0.1 (+https://github.com/NavesDev/job-hunter-ai)"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 1.0


class HttpClient(Protocol):
    """Fetches a page as text. The only I/O a job source is allowed to do."""

    def get(self, url: str) -> str: ...


class UrllibHttpClient:
    """A paced, self-identifying GET over the standard library — no new dependency."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout_seconds
        self._interval = min_request_interval_seconds
        self._last_request_at: float | None = None

    def get(self, url: str) -> str:
        self._keep_the_pace()
        request = urllib.request.Request(url, headers={"User-Agent": self._user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body: bytes = response.read()
        except urllib.error.HTTPError as exc:
            raise SourceError(f"geekhunter answered {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise SourceError(f"could not reach {url}: {exc}") from exc
        return body.decode("utf-8", errors="replace")

    def _keep_the_pace(self) -> None:
        """One request at a time, no faster than the configured interval."""
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self._interval:
                time.sleep(self._interval - elapsed)
        self._last_request_at = time.monotonic()
