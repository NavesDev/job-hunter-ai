import pytest

from job_hunter_ai.domain.entities.application_result import ApplicationStatus
from job_hunter_ai.domain.entities.smtp_config import SmtpConfig
from job_hunter_ai.domain.errors import SmtpError
from job_hunter_ai.infra.appliers.email_applier import REDACTED, EmailApplier
from tests.fakes import build_job, build_profile


def test_email_applier_should_deliver_the_message_to_the_local_server(smtp_server, tmp_path):
    # Arrange
    applier = EmailApplier(smtp_server.config)

    # Act
    applier.apply(build_job(apply_email="jobs@acme.com"), build_profile(tmp_path))

    # Assert
    assert len(smtp_server.messages) == 1
    assert smtp_server.handler.recipients[0] == ["jobs@acme.com"]


def test_email_applier_should_return_sent_when_the_server_accepts_the_message(
    smtp_server, tmp_path
):
    # Arrange
    job = build_job()
    applier = EmailApplier(smtp_server.config)

    # Act
    result = applier.apply(job, build_profile(tmp_path))

    # Assert
    assert result.status == ApplicationStatus.SENT
    assert (result.job_id, result.method, result.applier) == (job.id, "email", "email")
    assert result.applied_at is not None


def test_email_applier_should_carry_the_html_body_and_the_pdf_attachment(smtp_server, tmp_path):
    # Arrange
    applier = EmailApplier(smtp_server.config)

    # Act
    applier.apply(build_job(company="Acme"), build_profile(tmp_path))

    # Assert
    delivered = smtp_server.messages[0].decode("utf-8", errors="replace")
    assert "Acme" in delivered
    assert "application/pdf" in delivered
    assert "resume.pdf" in delivered


def test_email_applier_should_send_to_the_explicit_recipient_when_email_is_passed(
    smtp_server, tmp_path
):
    # Arrange
    applier = EmailApplier(smtp_server.config)

    # Act
    applier.apply(build_job(), build_profile(tmp_path), email="hr@acme.com")

    # Assert
    assert smtp_server.handler.recipients[0] == ["hr@acme.com"]


def test_email_applier_should_raise_smtp_error_when_the_server_refuses_the_message(
    rejecting_smtp_server, tmp_path
):
    # Arrange
    applier = EmailApplier(rejecting_smtp_server.config)

    # Act / Assert
    with pytest.raises(SmtpError) as error:
        applier.apply(build_job(), build_profile(tmp_path))
    assert error.value.code == "SMTP_ERROR"


def test_email_applier_should_redact_the_username_when_the_server_echoes_it_in_the_failure(
    rejecting_smtp_server, tmp_path
):
    # Arrange
    config = rejecting_smtp_server.config
    applier = EmailApplier(config)

    # Act
    with pytest.raises(SmtpError) as error:
        applier.apply(build_job(), build_profile(tmp_path))

    # Assert
    assert config.username not in str(error.value)
    assert REDACTED in str(error.value)


def test_email_applier_should_never_leak_the_password_when_the_connection_fails(tmp_path):
    # Arrange: port 1 is closed, so connecting raises before anything is sent
    config = SmtpConfig(
        host="127.0.0.1",
        port=1,
        username="ada@example.com",
        password="sup3r-s3cr3t",
        use_tls=False,
    )
    applier = EmailApplier(config)

    # Act
    with pytest.raises(SmtpError) as error:
        applier.apply(build_job(), build_profile(tmp_path))

    # Assert
    assert "sup3r-s3cr3t" not in str(error.value)
