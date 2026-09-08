"""The sign-in itself, on a page someone else opened.

Kept apart from the browser that runs it because two callers need it: `login-platform`,
which owns a browser to warm a profile, and the applier, which already has one open on a
job page and finds itself anonymous. GeekHunter's own cookies force that second case —
the token the job pages read (`auth_token`) is a session cookie, so it dies with every
browser, no matter what the profile holds.

The password is typed into the platform's field and nowhere else.
"""

from typing import Any

from job_hunter_ai.domain.entities.platform_credentials import PlatformCredentials
from job_hunter_ai.domain.errors import SessionError

SIGN_IN_PATH = "/pt/candidates/sign_in"
DASHBOARD_PATH = "/candidates/dashboard"
EMAIL_FIELD = "input[name='candidate[email]']"
PASSWORD_FIELD = "input[name='candidate[password]']"
REMEMBER_FIELD = "input[type='checkbox'][name='candidate[remember_me]']"
SUBMIT_FIELD = "input[name='commit']"
CONSENT_BUTTON = "ENTENDI E ACEITO"
JOB_EMAIL_FIELD = "input[name='email']"
_SETTLE_MS = 500


class GeekHunterSignIn:
    """Signs a browser page into GeekHunter, and can tell whether it already is."""

    def __init__(
        self, credentials: PlatformCredentials, base_url: str, timeout_ms: int = 30_000
    ) -> None:
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout_ms = timeout_ms

    def sign_in(self, page: Any) -> None:
        """Sign in, and take the candidate dashboard as the only proof that it worked."""
        self._open_sign_in(page)
        page.locator(EMAIL_FIELD).first.fill(self._credentials.username)
        page.locator(PASSWORD_FIELD).first.fill(self._credentials.password)
        self._remember_me(page)
        page.locator(SUBMIT_FIELD).first.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(_SETTLE_MS)
        if not self.landed_signed_in(page):
            raise SessionError(
                self._credentials.scrub(
                    "geekhunter refused the sign-in: the candidate dashboard is still out of "
                    f"reach{self._page_said(page)}; check "
                    f"{self._credentials.platform.upper()}_USERNAME and _PASSWORD in .env"
                )
            )

    def landed_signed_in(self, page: Any) -> bool:
        """The candidate dashboard is where a signed-in browser ends up, and nowhere else."""
        return DASHBOARD_PATH in str(page.url)

    def has_session(self, page: Any) -> bool:
        """Whether this browser is signed in, asked by opening the candidate area."""
        page.goto(f"{self._base_url}{SIGN_IN_PATH}", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        return self.landed_signed_in(page)

    def signed_in_on(self, page: Any) -> bool:
        """On a job page: a session fills the email field and locks it."""
        field = page.locator(JOB_EMAIL_FIELD)
        return bool(field.count()) and bool(field.first.is_disabled())

    def _open_sign_in(self, page: Any) -> None:
        """Load the sign-in page and clear the consent banner that covers the form."""
        page.goto(f"{self._base_url}{SIGN_IN_PATH}", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        consent = page.get_by_text(CONSENT_BUTTON, exact=False)
        if consent.count() and consent.first.is_visible():
            consent.first.click()
            page.wait_for_timeout(_SETTLE_MS)

    def _remember_me(self, page: Any) -> None:
        """Tick `Mantenha-me conectado`: it is what makes the platform remember at all."""
        remember = page.locator(REMEMBER_FIELD)
        if remember.count() == 0:
            return
        if not remember.first.is_checked():
            remember.first.check(force=True)
        if not remember.first.is_checked():
            raise SessionError(
                "could not tick `Mantenha-me conectado`; the sign-in page changed shape"
            )

    def _page_said(self, page: Any) -> str:
        """Whatever the platform put on the page, so a refusal says why."""
        try:
            text = " ".join(str(page.locator("body").first.inner_text()).split())
        except Exception:
            return ""
        for message in ("inválid", "incorret", "bloquead", "confirm"):
            found = next((line for line in text.split(". ") if message in line.lower()), "")
            if found:
                return f" ({found[:120]})"
        return ""
