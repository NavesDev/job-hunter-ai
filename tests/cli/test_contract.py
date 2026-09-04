from job_hunter_ai.cli.main import apply_job_app, list_jobs_app
from tests.cli.conftest import parse_stderr_json


def test_apply_job_should_exit_non_zero_with_structured_error_when_not_implemented(runner):
    # Arrange
    args = ["--job-id", "manual:a1b2c3", "--method", "email"]

    # Act
    result = runner.invoke(apply_job_app, args)

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "NOT_IMPLEMENTED"


def test_list_jobs_should_reject_call_when_required_source_flag_missing(runner):
    # Arrange
    args: list[str] = []

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert result.exit_code != 0
