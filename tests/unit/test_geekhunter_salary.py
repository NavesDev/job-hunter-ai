"""Choosing which predefined salary expectation goes into GeekHunter's form."""

import pytest

from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.infra.appliers import geekhunter_salary as salary

PROFILE = {
    "salary_expectation_clt": "4000",
    "salary_expectation_pj": "4500",
    "salary_expectation_internship": "2000",
}


@pytest.mark.parametrize(
    ("field_name", "expected"),
    [
        ("salaryExpectation.CLT", "4000"),
        ("salaryExpectation.PJ", "4500"),
        ("salaryExpectation.INT", "2000"),
    ],
)
def test_salary_should_follow_the_contract_type_the_form_asks_for(field_name, expected):
    # Arrange
    values = salary.configured(PROFILE)

    # Act
    chosen = salary.for_field(values, field_name, None)

    # Assert
    assert chosen == expected


def test_salary_should_prefer_the_caller_choice_over_the_contract_type_of_the_form():
    # Arrange
    values = salary.configured(PROFILE)

    # Act
    chosen = salary.for_field(values, "salaryExpectation.CLT", "pj")

    # Assert
    assert chosen == "4500"


def test_salary_should_raise_invalid_input_when_the_form_asks_for_a_contract_with_no_value():
    # Arrange
    values = salary.configured(PROFILE)

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        salary.for_field(values, "salaryExpectation.APP", None)
    assert "APP" in str(error.value) or "apprentice" in str(error.value)


def test_salary_should_fall_back_to_the_generic_value_when_one_is_configured():
    # Arrange
    values = salary.configured({"salary_expectation": "3000"})

    # Act
    chosen = salary.for_field(values, "salaryExpectation.TEMP", None)

    # Assert
    assert chosen == "3000"


def test_salary_should_reject_a_kind_the_profile_does_not_predefine():
    # Arrange
    values = salary.configured({"salary_expectation_clt": "4000"})

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        salary.require_choice(values, "pj")
    assert "clt" in str(error.value)
