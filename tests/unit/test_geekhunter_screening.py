"""`geekhunter_screening`: the rules an answer is checked against before a browser opens."""

import pytest

from job_hunter_ai.domain.errors import InvalidInputError
from job_hunter_ai.infra.appliers import geekhunter_screening as screening

NUMBER_QUESTION = {
    "id": 1,
    "name": "Quantos anos de experiência você tem?",
    "answerType": "number",
    "mandatory": True,
    "minAnswer": 1,
    "maxAnswer": 20,
}
OPTIONAL_BOOLEAN = {
    "id": 2,
    "name": "Aceita presencial?",
    "answerType": "boolean",
    "mandatory": False,
}


def test_asked_should_return_the_questions_recorded_on_the_job():
    # Arrange
    raw = {"screeningQuestions": [NUMBER_QUESTION, "not a question"]}

    # Act
    questions = screening.asked(raw)

    # Assert
    assert questions == [NUMBER_QUESTION]


def test_asked_should_return_nothing_when_the_job_has_no_payload():
    # Arrange / Act / Assert
    assert screening.asked(None) == []
    assert screening.asked({}) == []


def test_answers_for_should_map_every_answer_to_the_question_it_belongs_to():
    # Arrange
    questions = [NUMBER_QUESTION, OPTIONAL_BOOLEAN]

    # Act
    answers = screening.answers_for(questions, {"1": "3", "2": "sim"})

    # Assert
    assert answers == {"1": "3", "2": "Sim"}


def test_answers_for_should_leave_an_optional_question_unanswered():
    # Arrange / Act
    answers = screening.answers_for([NUMBER_QUESTION, OPTIONAL_BOOLEAN], {"1": "3"})

    # Assert
    assert answers == {"1": "3"}


def test_answers_for_should_raise_when_a_mandatory_question_has_no_answer():
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([NUMBER_QUESTION], {})
    assert "--answer 1=" in str(error.value)


def test_answers_for_should_raise_when_the_answer_is_not_the_number_the_question_asks():
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([NUMBER_QUESTION], {"1": "três"})
    assert "takes a number" in str(error.value)


def test_answers_for_should_raise_when_the_number_is_outside_the_range_the_question_allows():
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([NUMBER_QUESTION], {"1": "40"})
    assert "at most 20" in str(error.value)


def test_answers_for_should_raise_when_the_question_belongs_to_another_job():
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([NUMBER_QUESTION], {"1": "3", "99": "x"})
    assert "99" in str(error.value)


def test_answers_for_should_raise_when_a_boolean_answer_is_neither_yes_nor_no():
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([OPTIONAL_BOOLEAN], {"2": "talvez"})
    assert "sim" in str(error.value)


def test_answers_for_should_raise_when_the_answer_is_not_one_of_the_offered_options():
    # Arrange
    question = {
        "id": 3,
        "name": "Qual senioridade?",
        "answerType": "select",
        "options": ["Júnior", "Pleno"],
    }

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        screening.answers_for([question], {"3": "Sênior"})
    assert "Júnior, Pleno" in str(error.value)
