"""`GeekHunterSession` driving a real browser against a locally served sign-in page.

No test here reaches GeekHunter, and no real credential is used: the stand-in server
below accepts one made-up pair and sets its own cookie, exactly as Devise would.
"""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import pytest

from job_hunter_ai.domain.entities.platform_credentials import PlatformCredentials
from job_hunter_ai.domain.entities.session_result import SessionStatus
from job_hunter_ai.domain.errors import SessionError
from job_hunter_ai.infra.sessions.geekhunter_session import GeekHunterSession

pytest.importorskip("playwright", reason="signing in needs the `form` extra")

USERNAME = "ada@example.com"
PASSWORD = "not-a-real-password"
# The real page ships a consent banner that covers the form: an invisible field is not a
# session, and the strategy has to clear the banner before it can read the page at all.
SIGN_IN_FORM = """<html><body>
  <div id="consent" style="position:fixed;inset:0;background:#fff;z-index:9">
    <button type="submit" onclick="document.getElementById('consent').remove();
      document.getElementById('new_candidate').style.visibility='visible'">ENTENDI E ACEITO</button>
  </div>
  <form id="new_candidate" method="post" action="/pt/candidates/sign_in"
        style="visibility:hidden">
    <input type="email" name="candidate[email]" placeholder="Digite o seu email">
    <input type="password" name="candidate[password]" placeholder="Digite sua senha">
    <input type="checkbox" name="candidate[remember_me]">
    <input type="submit" name="commit" value="LOG IN">
  </form>
  <p>{message}</p>
</body></html>"""
SIGNED_IN = "<html><body><h1>Dashboard</h1><p>Olá! Que bom ver você de novo.</p></body></html>"
# The platform bounces a fresh browser here before it will show the candidate form.
CHOOSER = """<html><body><h1>Bem-vindo!</h1><p>Você é empresa ou candidato?</p>
  <a href="/pt/candidates/sign_in?chosen=1">SOU CANDIDATO</a>
  <a href="/pt/companies/sign_in">SOU EMPRESA</a></body></html>"""
DASHBOARD_PATH = "/v1/pt/candidates/dashboard"


class _Handler(BaseHTTPRequestHandler):
    """The sign-in page as Devise serves it: a form, a cookie, and nothing else."""

    def do_GET(self) -> None:
        signed_in = "session=1" in (self.headers.get("Cookie") or "")
        if self.path.startswith(DASHBOARD_PATH):
            # The candidate area bounces a visitor with no session, like the real one.
            self._send(
                SIGNED_IN if signed_in else CHOOSER, location=None if signed_in else "/pt/entrar"
            )
            return
        if signed_in:
            # Devise sends a signed-in visitor away from its own sign-in page.
            self._send(CHOOSER, location=DASHBOARD_PATH)
            return
        # A browser that has not said which kind of user it is gets the chooser first.
        self._send(SIGN_IN_FORM.format(message="") if "chosen=1" in self.path else CHOOSER)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        email = (form.get("candidate[email]") or [""])[0]
        password = (form.get("candidate[password]") or [""])[0]
        if (email, password) != (USERNAME, PASSWORD):
            self._send(SIGN_IN_FORM.format(message="Email ou senha inválidos."))
            return
        # Persistent, like the platform's "remember me": a session cookie would die
        # with the browser and the profile would be signed out on the next run.
        self._send(SIGNED_IN, cookie="session=1; Path=/; Max-Age=3600", location=DASHBOARD_PATH)

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


def credentials(password: str = PASSWORD) -> PlatformCredentials:
    return PlatformCredentials(platform="geekhunter", username=USERNAME, password=password)


def session_over(site: str, profile: Path, password: str = PASSWORD) -> GeekHunterSession:
    return GeekHunterSession(
        credentials(password),
        {"base_url": site, "browser_profile_dir": str(profile), "timeout_ms": 10_000},
    )


def test_session_should_sign_in_when_the_profile_has_none(site, tmp_path):
    # Arrange
    subject = session_over(site, tmp_path / "profile")

    # Act
    result = subject.ensure_session()

    # Assert
    assert result.status is SessionStatus.AUTHENTICATED
    assert result.source == "geekhunter"
    assert result.profile_dir == str(tmp_path / "profile")


def test_session_should_not_sign_in_again_when_the_profile_already_has_one(site, tmp_path):
    # Arrange
    profile = tmp_path / "profile"
    session_over(site, profile).ensure_session()

    # Act
    result = session_over(site, profile).ensure_session()

    # Assert
    assert result.status is SessionStatus.ALREADY_AUTHENTICATED


def test_session_should_sign_in_again_when_the_caller_forces_it(site, tmp_path):
    # Arrange
    profile = tmp_path / "profile"
    session_over(site, profile).ensure_session()

    # Act
    result = session_over(site, profile).ensure_session(force=True)

    # Assert
    assert result.status is SessionStatus.AUTHENTICATED


def test_session_should_raise_session_error_when_the_platform_refuses_the_credentials(
    site, tmp_path
):
    # Arrange
    subject = session_over(site, tmp_path / "profile", password="wrong-password")

    # Act / Assert
    with pytest.raises(SessionError) as error:
        subject.ensure_session()
    assert error.value.code == "SESSION_ERROR"
    assert "GEEKHUNTER_USERNAME" in str(error.value)


def test_session_should_never_put_the_password_in_the_error(site, tmp_path):
    # Arrange
    subject = session_over(site, tmp_path / "profile", password="wrong-password")

    # Act / Assert
    with pytest.raises(SessionError) as error:
        subject.ensure_session()
    assert "wrong-password" not in str(error.value)


def test_session_should_create_the_profile_directory_when_it_does_not_exist(site, tmp_path):
    # Arrange
    profile = tmp_path / "nested" / "profile"

    # Act
    session_over(site, profile).ensure_session()

    # Assert
    assert profile.is_dir()


def test_session_should_not_call_a_covered_form_a_session(site, tmp_path):
    """The consent banner hides the form; that is not the same as being signed in."""
    # Arrange
    subject = session_over(site, tmp_path / "profile", password="wrong-password")

    # Act / Assert
    with pytest.raises(SessionError):
        subject.ensure_session()  # a false `already_authenticated` would return instead


def test_session_should_sign_in_through_the_company_or_candidate_chooser(site, tmp_path):
    """The platform shows `empresa ou candidato?` before the form, and that is not an error."""
    # Arrange
    subject = session_over(site, tmp_path / "profile")

    # Act
    result = subject.ensure_session()

    # Assert
    assert result.status is SessionStatus.AUTHENTICATED
