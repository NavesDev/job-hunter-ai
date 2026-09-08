import json
from pathlib import Path

import pytest

from job_hunter_ai.cli.main import list_jobs_app, score_job_app
from job_hunter_ai.config.loader import CONFIG_PATH_ENV
from tests.cli.conftest import parse_stderr_json

RESUME = Path(__file__).resolve().parents[1] / "fixtures" / "resume" / "sample-resume.pdf"
UNREADABLE = RESUME.with_name("unreadable-resume.pdf")

CONTRACT_FIELDS = {
    "job_id",
    "source",
    "title",
    "company",
    "score",
    "verdict",
    "components",
    "required_skills",
    "preferred_skills",
    "experience",
    "knockouts",
    "resume_path",
    "scored_at",
}

ENTRY = {
    "title": "Backend Engineer",
    "company": "Acme",
    "url": "https://acme.com/jobs/1",
    "description": "Python, SQL, Kubernetes",
    "apply_email": "jobs@acme.com",
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An isolated repository root, with the sample résumé as the configured one."""
    config = tmp_path / "config.yaml"
    config.write_text(
        f'storage:\n  database_path: "{tmp_path / "jobs.db"}"\n'
        f'application:\n  resume_path: "{RESUME}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_PATH_ENV, str(config))
    return tmp_path


def collect_job(runner, workspace):
    path = workspace / "jobs.json"
    path.write_text(json.dumps([ENTRY]), encoding="utf-8")
    result = runner.invoke(list_jobs_app, ["--source", "manual", "--file", str(path)])
    return json.loads(result.stdout)[0]["id"]


def test_score_job_should_print_only_the_contract_json_on_stdout_when_the_job_exists(
    runner, workspace
):
    # Arrange
    job_id = collect_job(runner, workspace)

    # Act
    result = runner.invoke(score_job_app, ["--job-id", job_id])

    # Assert
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload) == CONTRACT_FIELDS
    assert payload["required_skills"]["matched"] == ["Python", "SQL"]
    assert payload["required_skills"]["missing"] == ["Kubernetes"]
    assert payload["scored_at"].endswith("Z")


def test_score_job_should_score_the_given_file_when_resume_is_passed(runner, workspace):
    # Arrange
    job_id = collect_job(runner, workspace)

    # Act
    result = runner.invoke(score_job_app, ["--job-id", job_id, "--resume", str(RESUME)])

    # Assert
    assert json.loads(result.stdout)["resume_path"] == str(RESUME)


def test_score_job_should_fail_with_job_not_found_when_the_job_was_never_collected(
    runner, workspace
):
    # Arrange
    collect_job(runner, workspace)

    # Act
    result = runner.invoke(score_job_app, ["--job-id", "manual:absent"])

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "JOB_NOT_FOUND"


def test_score_job_should_fail_with_invalid_input_when_the_resume_file_is_missing(
    runner, workspace
):
    # Arrange
    job_id = collect_job(runner, workspace)
    absent = workspace / "absent.pdf"

    # Act
    result = runner.invoke(score_job_app, ["--job-id", job_id, "--resume", str(absent)])

    # Assert
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"


def test_score_job_should_fail_with_resume_error_when_the_pdf_has_no_readable_text(
    runner, workspace
):
    # Arrange
    job_id = collect_job(runner, workspace)

    # Act
    result = runner.invoke(score_job_app, ["--job-id", job_id, "--resume", str(UNREADABLE)])

    # Assert
    assert parse_stderr_json(result)["code"] == "RESUME_ERROR"
