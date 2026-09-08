"""The applier signing itself in when a job page treats the browser as a stranger.

GeekHunter hands the job pages a token that lives only while a browser is open, so a
profile signed in yesterday opens today anonymous. The stand-in server below reproduces
exactly that: the job page is served anonymous until a sign-in happens in the same browser.
"""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from job_hunter_ai.domain.entities.application_result import ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.platform_credentials import PlatformCredentials
from job_hunter_ai.domain.errors import SessionError
from job_hunter_ai.infra.appliers.geekhunter_form import GeekHunterFormApplier
from job_hunter_ai.infra.sessions.geekhunter_sign_in import GeekHunterSignIn

pytest.importorskip("playwright", reason="applying through a form needs the `form` extra")

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "geekhunter"
USERNAME = "ada@example.com"
PASSWORD = "not-a-real-password"
DASHBOARD_PATH = "/v1/pt/candidates/dashboard"
SIGN_IN_PATH = "/pt/candidates/sign_in"
JOB_PATH = "/job"
SIGN_IN_FORM = """<html><body>
  <form id="new_candidate" method="post" action="/pt/candidates/sign_in">
    <input type="email" name="candidate[email]">
    <input type="password" name="candidate[password]">
    <input type="checkbox" name="candidate[remember_me]">
    <input type="submit" name="commit" value="LOG IN">
  </form>
</body></html>"""
DASHBOARD = "<html><body><h1>Dashboard</h1><p>Olá! Que bom ver você de novo.</p></body></html>"


class _Handler(BaseHTTPRequestHandler):
    """Serves the anonymous job page until this browser signs in, then the signed-in one."""

    def do_GET(self) -> None:
        signed_in = "session=1" in (self.headers.get("Cookie") or "")
        if self.path.startswith(JOB_PATH):
            page = "job-with-form-logged-in.html" if signed_in else "job-with-form.html"
            self._send(FIXTURES.joinpath(page).read_text(encoding="utf-8"))
            return
        if self.path.startswith(DASHBOARD_PATH):
            self._send(DASHBOARD if signed_in else "<html><body>Bem-vindo!</body></html>")
            return
        if signed_in:
            self._send(DASHBOARD, location=DASHBOARD_PATH)
            return
        self._send(SIGN_IN_FORM)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        given = (
            (form.get("candidate[email]") or [""])[0],
            (form.get("candidate[password]") or [""])[0],
        )
        if given != (USERNAME, PASSWORD):
            self._send(SIGN_IN_FORM)
            return
        self._send(DASHBOARD, cookie="session=1; Path=/", location=DASHBOARD_PATH)

    def _send(self, body: str, cookie: str | None = None, location: str | None = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(302 if location else 200)
        if location:
            self.send_header("Location", location)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: object) -> None:
        """Keep the test output pristine."""


@pytest.fixture
def site() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


@pytest.fixture
def profile(tmp_path: Path) -> CandidateProfile:
    resume = tmp_path / "resume.pdf"
    resume.write_bytes(b"%PDF-1.4\n%fake resume for the suite\n")
    return CandidateProfile(
        name="Ada Lovelace",
        contact_email=USERNAME,
        resume_path=resume,
        email_body_path=resume,
        extra_fields={
            "phone": "+55 61 99999-0000",
            "linkedin": "https://www.linkedin.com/in/ada",
            "salary_expectation": "8000",
        },
    )


def job_at(site: str) -> Job:
    return Job(
        id="geekhunter:abc123abc123",
        source="geekhunter",
        title="Desenvolvedor(a) .NET Júnior/Pleno",
        company="Agenda Digital Ltda.",
        url=f"{site}{JOB_PATH}",
    )


def sign_in_at(site: str, password: str = PASSWORD) -> GeekHunterSignIn:
    return GeekHunterSignIn(
        PlatformCredentials(platform="geekhunter", username=USERNAME, password=password),
        site,
        timeout_ms=10_000,
    )


def test_applier_should_sign_in_when_the_job_page_treats_the_browser_as_a_stranger(site, profile):
    # Arrange
    subject = GeekHunterFormApplier({"accept_terms": True, "submit": False}, sign_in_at(site))

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert "as the signed-in candidate" in result.detail
    assert result.status is ApplicationStatus.SKIPPED


def test_applier_should_apply_anonymously_when_no_credentials_are_configured(site, profile):
    # Arrange
    subject = GeekHunterFormApplier({"accept_terms": True, "submit": False}, None)

    # Act
    result = subject.apply(job_at(site), profile)

    # Assert
    assert "as an anonymous visitor" in result.detail


def test_applier_should_raise_session_error_when_the_platform_refuses_the_sign_in(site, profile):
    # Arrange
    subject = GeekHunterFormApplier(
        {"accept_terms": True, "submit": False}, sign_in_at(site, password="wrong-password")
    )

    # Act / Assert
    with pytest.raises(SessionError) as error:
        subject.apply(job_at(site), profile)
    assert "wrong-password" not in str(error.value)
