import json

import pytest

from job_hunter_ai.cli.main import list_jobs_app
from job_hunter_ai.config.loader import CONFIG_PATH_ENV
from tests.cli.conftest import parse_stderr_json

CONTRACT_FIELDS = {
    "id",
    "source",
    "title",
    "company",
    "description",
    "url",
    "apply_email",
    "raw",
    "collected_at",
}

ENTRY = {
    "title": "Backend Engineer",
    "company": "Acme",
    "url": "https://acme.com/jobs/1",
    "description": "Python, SQL",
    "apply_email": "jobs@acme.com",
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An isolated repository root: its own config file and its own database."""
    config = tmp_path / "config.yaml"
    config.write_text(f'storage:\n  database_path: "{tmp_path / "jobs.db"}"\n', encoding="utf-8")
    monkeypatch.setenv(CONFIG_PATH_ENV, str(config))
    return tmp_path


def write_jobs(workspace, payload=(ENTRY,)):
    path = workspace / "jobs.json"
    path.write_text(json.dumps(list(payload)), encoding="utf-8")
    return path


def test_list_jobs_should_print_only_the_contract_json_on_stdout_when_the_input_is_valid(
    runner, workspace
):
    # Arrange
    args = ["--source", "manual", "--file", str(write_jobs(workspace))]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload[0]) == CONTRACT_FIELDS
    assert payload[0]["id"].startswith("manual:")
    assert payload[0]["collected_at"].endswith("Z")


def test_list_jobs_should_return_the_same_ids_and_no_duplicates_when_run_twice(runner, workspace):
    # Arrange
    args = ["--source", "manual", "--file", str(write_jobs(workspace))]
    first = json.loads(runner.invoke(list_jobs_app, args).stdout)

    # Act
    second = json.loads(runner.invoke(list_jobs_app, args).stdout)

    # Assert
    assert [job["id"] for job in first] == [job["id"] for job in second]
    assert [job["collected_at"] for job in first] == [job["collected_at"] for job in second]


def test_list_jobs_should_cap_the_output_when_max_length_is_passed(runner, workspace):
    # Arrange
    entries = [{**ENTRY, "url": f"https://acme.com/jobs/{index}"} for index in range(4)]
    args = [
        "--source",
        "manual",
        "--file",
        str(write_jobs(workspace, entries)),
        "--max-length",
        "2",
    ]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert len(json.loads(result.stdout)) == 2


def test_list_jobs_should_create_the_database_at_the_configured_path_on_first_run(
    runner, workspace
):
    # Arrange
    args = ["--source", "manual", "--file", str(write_jobs(workspace))]

    # Act
    runner.invoke(list_jobs_app, args)

    # Assert
    assert (workspace / "jobs.db").is_file()


def test_list_jobs_should_fail_with_source_not_found_when_the_source_is_unknown(runner, workspace):
    # Arrange
    args = ["--source", "linkedin", "--file", str(write_jobs(workspace))]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "SOURCE_NOT_FOUND"


def test_list_jobs_should_fail_with_invalid_input_when_the_file_is_missing(runner, workspace):
    # Arrange
    args = ["--source", "manual", "--file", str(workspace / "absent.json")]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"


def test_list_jobs_should_fail_with_invalid_input_when_the_json_is_malformed(runner, workspace):
    # Arrange
    path = workspace / "jobs.json"
    path.write_text("{not json", encoding="utf-8")
    args = ["--source", "manual", "--file", str(path)]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"


def test_list_jobs_should_fail_with_invalid_input_when_max_length_is_not_positive(
    runner, workspace
):
    # Arrange
    args = ["--source", "manual", "--file", str(write_jobs(workspace)), "--max-length", "0"]

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert parse_stderr_json(result)["code"] == "INVALID_INPUT"
