"""Keeps a signed-in GeekHunter session in a browser profile of the tool's own.

Why a session at all: applying anonymously leaves the application waiting for a link
GeekHunter emails the candidate, so nothing is delivered until a human opens an inbox.
Signed in, the platform ties the application to the account and delivers it right away.

The password is typed into the platform's own field and nowhere else. It never reaches a
message, a log or the history — every error is scrubbed before it leaves this module
(docs/CODE_STANDARDS.md#error-policy).
"""

from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.platform_credentials import PlatformCredentials
from job_hunter_ai.domain.entities.session_result import SessionResult, SessionStatus
from job_hunter_ai.domain.errors import SessionError
from job_hunter_ai.domain.time_utils import utc_now

DEFAULT_BASE_URL = "https://www.geekhunter.com"
SIGN_IN_PATH = "/pt/candidates/sign_in"
EMAIL_FIELD = "input[name='candidate[email]']"
PASSWORD_FIELD = "input[name='candidate[password]']"
REMEMBER_FIELD = "input[type='checkbox'][name='candidate[remember_me]']"
SUBMIT_FIELD = "input[name='commit']"
DEFAULT_PROFILE_DIR = Path("config/local/browser-profile")
DEFAULT_TIMEOUT_MS = 30_000


class GeekHunterSession:
    """Signs the tool's browser profile into GeekHunter, and only when it has to."""

    name = "geekhunter"

    def __init__(
        self, credentials: PlatformCredentials, settings: dict[str, Any] | None = None
    ) -> None:
        settings = settings or {}
        self._credentials = credentials
        self._base_url = str(settings.get("base_url") or DEFAULT_BASE_URL).rstrip("/")
        self._profile_dir = Path(settings.get("browser_profile_dir") or DEFAULT_PROFILE_DIR)
        self._headless = bool(settings.get("headless", True))
        self._timeout_ms = int(settings.get("timeout_ms", DEFAULT_TIMEOUT_MS))

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
                        # Forcing means signing in again, and the form is only served to a
                        # browser the platform does not recognize yet.
                        context.clear_cookies()
                    page = context.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    return self._signed_in(page, force)
                finally:
                    context.close()
        except SessionError:
            raise
        except PlaywrightError as exc:
            raise SessionError(self._scrubbed(f"could not sign in to geekhunter: {exc}")) from None

    def _signed_in(self, page: Any, force: bool) -> SessionResult:
        page.goto(f"{self._base_url}{SIGN_IN_PATH}", wait_until="domcontentloaded")
        if not self._asking_for_credentials(page):
            if force:
                raise SessionError(
                    "geekhunter still recognizes this profile after clearing its cookies; "
                    "sign out by hand in the profile, or delete it and run login-platform again"
                )
            return self._result(SessionStatus.ALREADY_AUTHENTICATED, "the profile is signed in")
        self._fill_and_submit(page)
        if self._asking_for_credentials(page):
            raise SessionError(
                "geekhunter refused the sign-in and is still asking for credentials; "
                f"check {self._credentials.platform.upper()}_USERNAME and _PASSWORD in .env"
            )
        return self._result(SessionStatus.AUTHENTICATED, "signed in with the credentials in .env")

    def _asking_for_credentials(self, page: Any) -> bool:
        """The sign-in form on screen is the platform's own way of saying `no session`."""
        field = page.locator(PASSWORD_FIELD)
        return bool(field.count()) and bool(field.first.is_visible())

    def _fill_and_submit(self, page: Any) -> None:
        page.locator(EMAIL_FIELD).first.fill(self._credentials.username)
        page.locator(PASSWORD_FIELD).first.fill(self._credentials.password)
        remember = page.locator(REMEMBER_FIELD)
        # Without it the session dies with the browser, and the next run would sign in again.
        if remember.count() and not remember.first.is_checked():
            remember.first.dispatch_event("click")
        page.locator(SUBMIT_FIELD).first.click()
        page.wait_for_load_state("networkidle")

    def _result(self, status: SessionStatus, detail: str) -> SessionResult:
        return SessionResult(
            source=self.name,
            status=status,
            profile_dir=str(self._profile_dir),
            detail=detail,
            checked_at=utc_now(),
        )

    def _scrubbed(self, text: str) -> str:
        return self._credentials.scrub(text).splitlines()[0]
