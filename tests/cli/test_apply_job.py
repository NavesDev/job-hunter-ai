import json
import sqlite3

import pytest

from job_hunter_ai.cli.main import apply_job_app
from job_hunter_ai.config.loader import CONFIG_PATH_ENV
from job_hunter_ai.infra.repository.sqlite_job_repository import SqliteJobRepository
from tests.cli.conftest import parse_stderr_json
from tests.fakes import build_job

CONTRACT_FIELDS = {"job_id", "method", "status", "applier", "detail", "applied_at"}


@pytest.fixture
def workspace(tmp_path, smtp_server, monkeypatch):
    """An isolated root: its own config, database, resume, body template and SMTP server."""
    (tmp_path / "resume.pdf").write_bytes(b"%PDF-1.4 fake resume")
    (tmp_path / "email-body.html").write_text("<p>Hi {company}, I am {name}.</p>", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        "candidate:\n"
        '  name: "Ada Lovelace"\n'
        '  contact_email: "ada@example.com"\n'
        "application:\n"
        f'  resume_path: "{tmp_path / "resume.pdf"}"\n'
        f'  email_body_path: "{tmp_path / "email-body.html"}"\n'
        '  default_subject: "Application - {title} - Ada"\n'
        "storage:\n"
        f'  database_path: "{tmp_path / "jobs.db"}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_PATH_ENV, str(config))
    monkeypatch.setenv("SMTP_HOST", smtp_server.config.host)
    monkeypatch.setenv("SMTP_PORT", str(smtp_server.config.port))
    monkeypatch.setenv("SMTP_USERNAME", smtp_server.config.username)
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    return tmp_path


def seed_job(workspace, **overrides):
    job = build_job(**overrides)
    with SqliteJobRepository(workspace / "jobs.db") as repository:
        repository.save_jobs([job])
    return job


def applications(workspace):
    with sqlite3.connect(workspace / "jobs.db") as connection:
        return connection.execute("SELECT status, detail FROM applications").fetchall()


def test_apply_job_should_print_the_contract_result_when_the_email_is_sent(
    runner, workspace, smtp_server
):
    # Arrange
    job = seed_job(workspace, apply_email="jobs@acme.com")

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == CONTRACT_FIELDS
    assert payload["status"] == "sent"
    assert payload["applied_at"].endswith("Z")
    assert len(smtp_server.messages) == 1


def test_apply_job_should_send_to_the_flag_recipient_when_email_is_passed(
    runner, workspace, smtp_server
):
    # Arrange
    job = seed_job(workspace, apply_email="jobs@acme.com")

    # Act
    runner.invoke(
        apply_job_app,
        ["--job-id", job.id, "--method", "email", "--email", "hr@acme.com", "--subject", "Hello"],
    )

    # Assert
    assert smtp_server.handler.recipients[0] == ["hr@acme.com"]
    assert "Subject: Hello" in smtp_server.messages[0].decode("utf-8", errors="replace")


def test_apply_job_should_record_the_attempt_in_the_history_when_it_succeeds(runner, workspace):
    # Arrange
    job = seed_job(workspace)

    # Act
    runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert [row[0] for row in applications(workspace)] == ["sent"]


def test_apply_job_should_return_skipped_with_exit_zero_when_the_method_is_form(runner, workspace):
    # Arrange
    job = seed_job(workspace)

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "form"])

    # Assert
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "skipped"


def test_apply_job_should_fail_with_job_not_found_when_the_id_is_unknown(runner, workspace):
    # Arrange
    seed_job(workspace)

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", "manual:deadbeefcafe", "--method", "email"])

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "JOB_NOT_FOUND"


def test_apply_job_should_fail_with_invalid_input_when_there_is_no_recipient(runner, workspace):
    # Arrange
    job = seed_job(workspace, apply_email=None)

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"


def test_apply_job_should_fail_with_applier_not_found_when_the_method_is_unknown(runner, workspace):
    # Arrange
    job = seed_job(workspace)

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "carrier-pigeon"])

    # Assert
    assert parse_stderr_json(result)["code"] == "APPLIER_NOT_FOUND"


def test_apply_job_should_fail_with_invalid_input_when_all_ready_is_requested(runner, workspace):
    # Arrange
    job = seed_job(workspace)

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email", "--all-ready"])

    # Assert
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"


def test_apply_job_should_fail_with_smtp_error_when_the_server_is_unreachable(
    runner, workspace, monkeypatch
):
    # Arrange
    job = seed_job(workspace)
    monkeypatch.setenv("SMTP_PORT", "1")

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "SMTP_ERROR"


def test_apply_job_should_record_a_failed_attempt_when_the_server_is_unreachable(
    runner, workspace, monkeypatch
):
    # Arrange
    job = seed_job(workspace)
    monkeypatch.setenv("SMTP_PORT", "1")

    # Act
    runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert [row[0] for row in applications(workspace)] == ["failed"]


def test_apply_job_should_never_leak_the_password_when_the_send_fails(
    runner, workspace, monkeypatch
):
    # Arrange
    job = seed_job(workspace)
    monkeypatch.setenv("SMTP_PORT", "1")

    # Act
    result = runner.invoke(apply_job_app, ["--job-id", job.id, "--method", "email"])

    # Assert
    assert "app-password" not in (result.stderr or result.output)
    assert all("app-password" not in row[1] for row in applications(workspace))
