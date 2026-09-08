"""Warms a browser profile with a GeekHunter session, for `login-platform`.

Why a session at all: signed in, the job form arrives with the candidate's own data and
the application is delivered when submitted. Anonymous, GeekHunter holds it until the
candidate clicks a link it emails them.

The browser lifecycle lives here; the sign-in steps live in `geekhunter_sign_in`, because
the applier performs the same sign-in on a page it already has open.
"""

from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.platform_credentials import PlatformCredentials
from job_hunter_ai.domain.entities.session_result import SessionResult, SessionStatus
from job_hunter_ai.domain.errors import SessionError
from job_hunter_ai.domain.time_utils import utc_now
from job_hunter_ai.infra.sessions.geekhunter_sign_in import GeekHunterSignIn

DEFAULT_BASE_URL = "https://www.geekhunter.com"
DEFAULT_PROFILE_DIR = Path("config/local/browser-profile")
DEFAULT_TIMEOUT_MS = 30_000


class GeekHunterSession:
    """Signs the tool's browser profile into GeekHunter, and only when it has to."""

    name = "geekhunter"

    def __init__(
        self, credentials: PlatformCredentials, settings: dict[str, Any] | None = None
    ) -> None:
        settings = settings or {}
        self._base_url = str(settings.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
        self._profile_dir = Path(settings.get("browser_profile_dir") or DEFAULT_PROFILE_DIR)
        self._headless = bool(settings.get("headless", True))
        self._timeout_ms = int(settings.get("timeout_ms", DEFAULT_TIMEOUT_MS))
        self._sign_in = GeekHunterSignIn(credentials, self._base_url, self._timeout_ms)

    def ensure_session(self, force: bool = False) -> SessionResult:
        """Return a usable session, signing in only when the profile has none."""
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        self._profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    str(self._profile_dir), headless=self._headless
                )
                try:
                    if force:
                        # The form is only served to a browser the platform does not
                        # recognize yet, so forcing means forgetting first.
                        context.clear_cookies()
                    page = context.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    return self._session(page, force)
                finally:
                    context.close()
        except SessionError:
            raise
        except PlaywrightError as exc:
            raise SessionError(f"could not sign in to geekhunter: {_first_line(exc)}") from None

    def _session(self, page: Any, force: bool) -> SessionResult:
        if not force and self._sign_in.has_session(page):
            return self._result(SessionStatus.ALREADY_AUTHENTICATED, "the profile is signed in")
        self._sign_in.sign_in(page)
        return self._result(
            SessionStatus.AUTHENTICATED,
            "signed in with the credentials in .env; the platform's own token for the job "
            "pages lasts only while a browser is open, so apply-job signs in again as needed",
        )

    def _result(self, status: SessionStatus, detail: str) -> SessionResult:
        return SessionResult(
            source=self.name,
            status=status,
            profile_dir=str(self._profile_dir),
            detail=detail,
            checked_at=utc_now(),
        )


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__
