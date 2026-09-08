"""The screening questions a GeekHunter job asks after its form, and the answers given.

Everything here happens *before* the browser opens. A mandatory question discovered on
the screen with the form already submitted leaves the candidacy half-made, so `--answer`
is checked against the questions `list-jobs` recorded: every answer belongs to a question
of this job, every mandatory question has one, and every value fits the type asked for.

Nothing is ever answered on the candidate's behalf. These questions are about their own
experience, and a value invented here would be a claim made in their name.
"""

from typing import Any

from job_hunter_ai.domain.errors import InvalidInputError

QUESTIONS_KEY = "screeningQuestions"
NUMBER = "number"
BOOLEAN = "boolean"
BOOLEAN_VALUES = {
    "sim": "Sim",
    "true": "Sim",
    "yes": "Sim",
    "não": "Não",
    "nao": "Não",
    "false": "Não",
    "no": "Não",
}


def asked(job_raw: Any) -> list[dict[str, Any]]:
    """The questions recorded for the job, or none when it asks nothing."""
    if not isinstance(job_raw, dict):
        return []
    questions = job_raw.get(QUESTIONS_KEY)
    return (
        [question for question in questions if isinstance(question, dict)]
        if isinstance(questions, list)
        else []
    )


def answers_for(questions: list[dict[str, Any]], given: Any) -> dict[str, str]:
    """Map every question id to the answer that will be typed, raising on any mismatch."""
    given = _mapping(given)
    known = {str(question.get("id")): question for question in questions}
    _unknown(given, known)
    answers: dict[str, str] = {}
    for identifier, question in known.items():
        raw = given.get(identifier)
        if raw is None:
            _required(question, identifier)
            continue
        answers[identifier] = _value(question, identifier, str(raw).strip())
    return answers


def _mapping(given: Any) -> dict[str, str]:
    if given is None:
        return {}
    if not isinstance(given, dict):
        raise InvalidInputError("`--answer` must be given as `question-id=value`")
    return {str(key).strip(): value for key, value in given.items()}


def _unknown(given: dict[str, str], known: dict[str, dict[str, Any]]) -> None:
    strangers = sorted(set(given) - set(known))
    if not strangers:
        return
    asked_ids = ", ".join(sorted(known)) or "none"
    raise InvalidInputError(
        f"no screening question `{strangers[0]}` on this job; it asks: {asked_ids}"
    )


def _required(question: dict[str, Any], identifier: str) -> None:
    if question.get("mandatory"):
        raise InvalidInputError(
            f"the job asks `{question.get('name')}` and the answer is mandatory; "
            f"pass it as `--answer {identifier}=<value>`"
        )


def _value(question: dict[str, Any], identifier: str, text: str) -> str:
    if not text:
        raise InvalidInputError(f"the answer to the screening question `{identifier}` is empty")
    kind = str(question.get("answerType") or "").lower()
    if kind == NUMBER:
        return _number(question, identifier, text)
    if kind == BOOLEAN:
        return _boolean(identifier, text)
    return _option(question, identifier, text)


def _number(question: dict[str, Any], identifier: str, text: str) -> str:
    try:
        number = float(text.replace(",", "."))
    except ValueError as exc:
        raise InvalidInputError(
            f"the screening question `{identifier}` takes a number, got `{text}`"
        ) from exc
    _within(question, identifier, number, text)
    return text


def _within(question: dict[str, Any], identifier: str, number: float, text: str) -> None:
    for bound, limit in (
        ("minAnswer", question.get("minAnswer")),
        ("maxAnswer", question.get("maxAnswer")),
    ):
        if limit is None:
            continue
        too_low = bound == "minAnswer" and number < float(limit)
        too_high = bound == "maxAnswer" and number > float(limit)
        if too_low or too_high:
            raise InvalidInputError(
                f"the screening question `{identifier}` takes a number "
                f"{'at least' if too_low else 'at most'} {limit}, got `{text}`"
            )


def _boolean(identifier: str, text: str) -> str:
    answer = BOOLEAN_VALUES.get(text.lower())
    if answer is None:
        raise InvalidInputError(
            f"the screening question `{identifier}` takes `sim` or `não`, got `{text}`"
        )
    return answer


def _option(question: dict[str, Any], identifier: str, text: str) -> str:
    options = [str(option) for option in question.get("options") or [] if str(option).strip()]
    if options and text not in options:
        raise InvalidInputError(
            f"unknown answer `{text}` for the screening question `{identifier}`; "
            f"it offers: {', '.join(options)}"
        )
    return text
