import pytest

from job_hunter_ai.domain.errors import SourceNotFoundError
from job_hunter_ai.infra.sources.manual_json import ManualJsonJobSource
from job_hunter_ai.infra.sources.registry import SourceRegistry
from tests.fakes import FakeJobSource


def test_source_registry_should_build_the_manual_source_when_asked_by_name():
    # Arrange
    registry = SourceRegistry()

    # Act
    source = registry.get("manual")

    # Assert
    assert isinstance(source, ManualJsonJobSource)


def test_source_registry_should_raise_source_not_found_when_the_name_is_unknown():
    # Arrange
    registry = SourceRegistry()

    # Act / Assert
    with pytest.raises(SourceNotFoundError) as error:
        registry.get("linkedin")
    assert error.value.code == "SOURCE_NOT_FOUND"


def test_source_registry_should_expose_a_new_platform_when_it_is_registered():
    # Arrange
    registry = SourceRegistry()

    # Act
    registry.register("fake", FakeJobSource)

    # Assert
    assert "fake" in registry.available()
    assert isinstance(registry.get("fake"), FakeJobSource)
