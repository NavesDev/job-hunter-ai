from job_hunter_ai.cli.main import apply_job_app, list_jobs_app


def test_list_jobs_should_reject_call_when_required_source_flag_missing(runner):
    # Arrange
    args: list[str] = []

    # Act
    result = runner.invoke(list_jobs_app, args)

    # Assert
    assert result.exit_code != 0


def test_apply_job_should_reject_call_when_required_method_flag_missing(runner):
    # Arrange
    args = ["--job-id", "manual:a1b2c3"]

    # Act
    result = runner.invoke(apply_job_app, args)

    # Assert
    assert result.exit_code != 0
