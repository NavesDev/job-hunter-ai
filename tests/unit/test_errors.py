import pytest

from job_hunter_ai.domain import errors


@pytest.mark.parametrize(
    ("error_class", "expected_code"),
    [
        (errors.SourceNotFoundError, "SOURCE_NOT_FOUND"),
        (errors.ApplierNotFoundError, "APPLIER_NOT_FOUND"),
        (errors.JobNotFoundError, "JOB_NOT_FOUND"),
        (errors.SmtpError, "SMTP_ERROR"),
        (errors.InvalidInputError, "INVALID_INPUT"),
    ],
)
def test_domain_error_should_carry_documented_code_when_raised(error_class, expected_code):
    # Arrange
    error = error_class("mensagem qualquer")

    # Act
    code = error.code

    # Assert
    assert code == expected_code
