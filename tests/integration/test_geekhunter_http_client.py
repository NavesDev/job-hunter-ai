"""`UrllibHttpClient` against a local HTTP server. It never leaves the machine."""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from job_hunter_ai.domain.errors import PageNotFoundError, SourceError
from job_hunter_ai.infra.sources.geekhunter.http_client import UrllibHttpClient

NO_PACE = 0.0


_REFUSED = {"/forbidden": 403, "/missing": 404}


class _Handler(BaseHTTPRequestHandler):
    """Echoes the user-agent, refuses `/forbidden` and has no `/missing`, like the real site."""

    def do_GET(self) -> None:
        if self.path in _REFUSED:
            self.send_response(_REFUSED[self.path])
            self.end_headers()
            return
        body = f"user-agent: {self.headers.get('User-Agent')}".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Keep the test output pristine."""


@pytest.fixture
def server() -> Iterator[str]:
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_client_should_identify_itself_because_the_cdn_rejects_the_default_agent(server):
    # Arrange
    client = UrllibHttpClient(user_agent="job-hunter-ai/test", min_request_interval_seconds=NO_PACE)

    # Act
    body = client.get(f"{server}/vagas")

    # Assert
    assert body == "user-agent: job-hunter-ai/test"


def test_http_client_should_raise_source_error_when_the_platform_refuses_the_request(server):
    # Arrange
    client = UrllibHttpClient(min_request_interval_seconds=NO_PACE)

    # Act / Assert
    with pytest.raises(SourceError) as error:
        client.get(f"{server}/forbidden")
    assert error.value.code == "SOURCE_ERROR"
    assert "403" in str(error.value)


def test_http_client_should_raise_source_error_when_the_host_is_unreachable():
    # Arrange
    client = UrllibHttpClient(min_request_interval_seconds=NO_PACE)

    # Act / Assert
    with pytest.raises(SourceError):
        client.get("http://127.0.0.1:1/vagas")


def test_http_client_should_keep_a_minimum_interval_between_two_requests(server):
    # Arrange
    client = UrllibHttpClient(min_request_interval_seconds=0.25)
    slept: list[float] = []

    # Act
    client.get(f"{server}/first")
    import time

    started = time.monotonic()
    client.get(f"{server}/second")
    slept.append(time.monotonic() - started)

    # Assert
    assert slept[0] >= 0.2


def test_http_client_should_raise_page_not_found_when_the_page_does_not_exist(server):
    # Arrange
    client = UrllibHttpClient(min_request_interval_seconds=NO_PACE)

    # Act / Assert
    with pytest.raises(PageNotFoundError) as error:
        client.get(f"{server}/missing")
    assert error.value.code == "SOURCE_ERROR"  # a 404 is still a source failure to a caller
    assert "404" in str(error.value)
