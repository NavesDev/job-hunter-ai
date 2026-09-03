from job_hunter_ai.domain.entities import ApplicationResult, ApplicationStatus


def test_application_result_should_expose_status_as_contract_string_when_serialized():
    # Arrange
    result = ApplicationResult(
        job_id="manual:a1b2c3",
        method="email",
        status=ApplicationStatus.SENT,
        applier="email",
    )

    # Act
    status = str(result.status)

    # Assert
    assert status == "sent"


def test_application_status_should_have_only_contract_values_when_enumerated():
    # Arrange
    expected = {"sent", "failed", "skipped"}

    # Act
    actual = {str(status) for status in ApplicationStatus}

    # Assert
    assert actual == expected
