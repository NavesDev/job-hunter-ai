"""Requirements extraction against the pages and payloads the platforms really publish."""

import json
from pathlib import Path

from job_hunter_ai.infra.requirements.geekhunter_requirements import (
    GeekHunterRequirementsExtractor,
)
from job_hunter_ai.infra.requirements.generic_requirements import GenericRequirementsExtractor
from job_hunter_ai.infra.requirements.registry import ExtractorRegistry
from job_hunter_ai.infra.sources.geekhunter import parser
from tests.fakes import build_job

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "geekhunter" / "job-detail-1.html"


def geekhunter_job():
    posting = parser.job_posting(FIXTURE.read_text(encoding="utf-8"), "https://geekhunter.test")
    return build_job(
        source="geekhunter",
        title=str(posting["title"]).strip(),
        description=str(posting["description"]),
        raw=json.loads(json.dumps(posting)),
    )


def test_geekhunter_extractor_should_read_the_skills_field_when_the_posting_declares_it():
    # Arrange
    job = geekhunter_job()

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert "Next.js" in requirements.required
    assert (
        requirements.months_of_experience == job.raw["experienceRequirements"]["monthsOfExperience"]
    )


def test_geekhunter_extractor_should_drop_the_years_line_when_the_requisitos_list_states_it():
    # Arrange
    job = geekhunter_job()

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert not any("anos de experi" in term.casefold() for term in requirements.required)


def test_geekhunter_extractor_should_fill_the_preferred_bucket_when_the_description_has_one():
    # Arrange
    job = geekhunter_job()

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert requirements.preferred
    assert not set(requirements.preferred) & set(requirements.required)


def test_generic_extractor_should_split_the_description_when_the_source_has_no_structure():
    # Arrange
    job = build_job(description="Python, SQL e Docker")

    # Act
    requirements = GenericRequirementsExtractor().extract(job)

    # Assert
    assert requirements.required == ("Python", "SQL", "Docker")
    assert requirements.months_of_experience is None


def test_extractor_registry_should_fall_back_to_the_generic_one_when_the_source_is_unknown():
    # Arrange
    registry = ExtractorRegistry()

    # Act
    extractor = registry.get("linkedin")

    # Assert
    assert extractor.name == GenericRequirementsExtractor.name


EMPHASIZED = (
    "<p><strong>Requisitos</strong></p>"
    "<ul><li>3+ anos de experiência na carreira</li>"
    "<li>Conhecimento em <strong>Java 8 ou superior</strong></li>"
    "<li>Vivência com <strong>Docker e Kubernetes</strong></li></ul>"
    "<p><strong>Diferenciais</strong></p><ul><li><strong>Kafka</strong></li></ul>"
    "<p><strong>Responsabilidades</strong></p>"
    "<ul><li>Escrever <strong>relatórios</strong></li></ul>"
)


def test_geekhunter_extractor_should_keep_only_the_emphasized_skill_when_it_sits_in_a_sentence():
    # Arrange
    job = build_job(source="geekhunter", description=EMPHASIZED, raw={"skills": ""})

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert requirements.required == ("Java", "Docker", "Kubernetes")


def test_geekhunter_extractor_should_read_the_diferenciais_list_as_preferred_when_it_exists():
    # Arrange
    job = build_job(source="geekhunter", description=EMPHASIZED, raw={"skills": ""})

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert requirements.preferred == ("Kafka",)


def test_geekhunter_extractor_should_ignore_a_list_when_its_heading_is_not_about_requirements():
    # Arrange
    job = build_job(source="geekhunter", description=EMPHASIZED, raw={"skills": ""})

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert "relatórios" not in requirements.required + requirements.preferred


def test_geekhunter_extractor_should_keep_a_leading_dot_when_it_belongs_to_the_skill_name():
    # Arrange
    job = build_job(source="geekhunter", description="", raw={"skills": ".NET, C#, Docker."})

    # Act
    requirements = GeekHunterRequirementsExtractor().extract(job)

    # Assert
    assert requirements.required == (".NET", "C#", "Docker")
