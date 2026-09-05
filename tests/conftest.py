"""A local fake SMTP server. No test in this suite ever sends a real email."""

import socket
from collections.abc import Iterator

import pytest
from aiosmtpd.controller import Controller

from job_hunter_ai.domain.entities.smtp_config import SmtpConfig


class RecordingHandler:
    """Accepts every message and keeps it in memory, unless told to reject the sender."""

    def __init__(self, reject_sender: bool = False):
        self.messages: list[bytes] = []
        self.recipients: list[list[str]] = []
        self.reject_sender = reject_sender

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        if self.reject_sender:
            return f"550 rejected sender {address}"
        envelope.mail_from = address
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope.content)
        self.recipients.append(list(envelope.rcpt_tos))
        return "250 Message accepted"


class FakeSmtpServer:
    def __init__(self, controller: Controller, handler: RecordingHandler):
        self._controller = controller
        self.handler = handler
        self.port = controller.port

    @property
    def config(self) -> SmtpConfig:
        """Credentials pointing at this server. TLS off and no password: it is local."""
        return SmtpConfig(
            host=self._controller.hostname,
            port=self.port,
            username="ada@example.com",
            password="",
            use_tls=False,
        )

    @property
    def messages(self) -> list[bytes]:
        return self.handler.messages


def _free_port() -> int:
    """aiosmtpd's readiness check connects to the configured port, so it cannot be 0."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _start(handler: RecordingHandler) -> Iterator[FakeSmtpServer]:
    controller = Controller(handler, hostname="127.0.0.1", port=_free_port())
    controller.start()
    try:
        yield FakeSmtpServer(controller, handler)
    finally:
        controller.stop()


@pytest.fixture
def smtp_server() -> Iterator[FakeSmtpServer]:
    yield from _start(RecordingHandler())


@pytest.fixture
def rejecting_smtp_server() -> Iterator[FakeSmtpServer]:
    yield from _start(RecordingHandler(reject_sender=True))
