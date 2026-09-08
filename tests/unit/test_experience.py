from datetime import date

from job_hunter_ai.domain.matching.experience import total_months

TODAY = date(2026, 9, 8)
HEADING = "EXPERIENCIA PROFISSIONAL\n"


def test_total_months_should_count_a_closed_range_inclusively_when_both_ends_are_dated():
    # Arrange
    text = f"{HEADING}Acme - Dev 01/2020 - 12/2020"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 12


def test_total_months_should_count_until_today_when_the_position_is_ongoing():
    # Arrange
    text = f"{HEADING}Acme - Dev jan/2026 - atual"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 9


def test_total_months_should_count_until_today_when_the_position_only_has_a_start():
    # Arrange
    text = f"{HEADING}Acme - Dev desde 12/2025"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 10


def test_total_months_should_count_an_overlap_once_when_two_positions_run_together():
    # Arrange
    text = f"{HEADING}Acme 01/2020 - 12/2020\nGlobex 06/2020 - 12/2020"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 12


def test_total_months_should_ignore_the_degree_dates_when_the_resume_has_an_education_section():
    # Arrange
    text = f"{HEADING}Acme 01/2026 - 06/2026\nFORMACAO ACADEMICA\nUNIP 2016 - 2020"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 6


def test_total_months_should_be_zero_when_the_resume_states_no_date():
    # Arrange
    text = f"{HEADING}Acme - Dev por varios anos"

    # Act
    result = total_months(text, TODAY)

    # Assert
    assert result == 0
