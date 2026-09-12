from job_hunter_ai.domain.matching.contact import has_email, has_phone, is_reachable


def test_has_email_should_find_the_address_when_it_carries_no_label():
    # Arrange
    text = "Asa Sul - Brasilia - DF | davi.naves@example.com | github.com/user"

    # Act
    result = has_email(text)

    # Assert
    assert result is True


def test_has_phone_should_find_a_brazilian_number_when_it_has_an_area_code():
    # Arrange
    text = "Brasilia - DF | (61) 92004-9576 | davi@example.com"

    # Act
    result = has_phone(text)

    # Assert
    assert result is True


def test_has_phone_should_find_a_foreign_number_when_it_is_written_with_dashes():
    # Arrange
    text = "Cambridge, MA 02318 - 617-495-2595"

    # Act
    result = has_phone(text)

    # Assert
    assert result is True


def test_has_phone_should_refuse_a_date_range_when_it_looks_like_two_years():
    # Arrange
    text = "Bachelor of Arts in Computer Science 2018-2021"

    # Act
    result = has_phone(text)

    # Assert
    assert result is False


def test_is_reachable_should_be_false_when_the_resume_carries_no_address_or_number():
    # Arrange
    text = "EXPERIENCIA PROFISSIONAL Acme - Dev 01/2020 - 12/2022 Python"

    # Act
    result = is_reachable(text)

    # Assert
    assert result is False
