from job_hunter_ai.domain.entities.ats_score import ScoreVerdict
from job_hunter_ai.domain.entities.job_requirements import JobRequirements
from job_hunter_ai.domain.matching.ats_scorer import WEIGHTS, AtsScorer
from tests.fakes import build_job, build_resume

RESUME_TEXT = (
    "Alex Candidate alex@example.com\n"
    "RESUMO Desenvolvedor backend\n"
    "EXPERIENCIA PROFISSIONAL Acme - Dev 01/2020 - 12/2022 Python e Docker\n"
    "FORMACAO ACADEMICA Universidade Exemplo 2016 - 2019\n"
    "HABILIDADES Python, Docker, SQL\n"
)


def test_score_should_split_the_requirements_into_matched_and_missing_when_some_are_absent():
    # Arrange
    requirements = JobRequirements(required=("Python", "Kubernetes"))

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT))

    # Assert
    assert score.required_skills.matched == ("Python",)
    assert score.required_skills.missing == ("Kubernetes",)
    assert score.components["required_skills"] == 50.0


def test_score_should_reach_a_hundred_when_the_resume_answers_every_requirement():
    # Arrange
    requirements = JobRequirements(title="Desenvolvedor", required=("Python", "Docker", "SQL"))

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT, pages=1))

    # Assert
    assert score.components["required_skills"] == 100.0
    assert score.verdict == ScoreVerdict.STRONG


def test_score_should_not_punish_the_resume_when_the_posting_lists_no_requirement():
    # Arrange
    requirements = JobRequirements()

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT))

    # Assert
    assert score.components["required_skills"] == 100.0
    assert score.components["preferred_skills"] == 100.0


def test_score_should_return_a_knockout_verdict_when_the_experience_is_below_the_minimum():
    # Arrange
    requirements = JobRequirements(required=("Python", "Docker", "SQL"), months_of_experience=120)

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT))

    # Assert
    assert score.verdict == ScoreVerdict.KNOCKOUT
    assert score.knockouts[0].rule == "min_experience"
    assert score.knockouts[0].passed is False
    assert score.experience.detected_months == 36


def test_score_should_report_no_knockout_when_the_posting_asks_for_no_experience():
    # Arrange
    requirements = JobRequirements(required=("Python",))

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT))

    # Assert
    assert score.knockouts == ()
    assert score.components["experience"] == 100.0


def test_score_should_collapse_the_parseability_when_the_pages_yield_almost_no_text():
    # Arrange
    resume = build_resume("Alex Candidate - Python", pages=3)

    # Act
    score = AtsScorer().score(build_job(), JobRequirements(), resume)

    # Assert
    assert score.components["parseability"] < 5.0


def test_score_should_be_the_weighted_sum_of_its_components_when_it_is_computed():
    # Arrange
    requirements = JobRequirements(required=("Python", "Kubernetes"), months_of_experience=24)

    # Act
    score = AtsScorer().score(build_job(), requirements, build_resume(RESUME_TEXT))

    # Assert
    expected = sum(score.components[name] * weight for name, weight in WEIGHTS.items()) / 100
    assert score.score == round(expected, 1)


def test_score_should_count_the_contact_section_when_the_resume_only_prints_its_values():
    # Arrange
    resume = build_resume(f"Davi Naves davi@example.com (61) 92004-9576\n{RESUME_TEXT}")

    # Act
    score = AtsScorer().score(build_job(), JobRequirements(), resume)

    # Assert
    assert score.components["sections"] == 100.0
