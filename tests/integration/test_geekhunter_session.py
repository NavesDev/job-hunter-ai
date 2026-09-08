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
SIGN_IN_FORM = """<html><body>
  <form id="new_candidate" method="post" action="/pt/candidates/sign_in">
    <input type="email" name="candidate[email]" placeholder="Digite o seu email">
    <input type="password" name="candidate[password]" placeholder="Digite sua senha">
    <input type="checkbox" name="candidate[remember_me]">
    <input type="submit" name="commit" value="LOG IN">
  </form>
  <p>{message}</p>
</body></html>"""
SIGNED_IN = "<html><body><h1>Minhas candidaturas</h1><p>Você está conectado.</p></body></html>"


class _Handler(BaseHTTPRequestHandler):
    """The sign-in page as Devise serves it: a form, a cookie, and nothing else."""

    def do_GET(self) -> None:
        if "session=1" in (self.headers.get("Cookie") or ""):
            self._send(SIGNED_IN)
            return
        self._send(SIGN_IN_FORM.format(message=""))

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
        self._send(SIGNED_IN, cookie="session=1; Path=/; Max-Age=3600")

    def _send(self, body: str, cookie: str | None = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(200)
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
