from job_hunter_ai.infra.appliers.registry import ANY_SOURCE, ApplierRegistry
from tests.fakes import FakeJobApplier


def test_applier_registry_should_return_the_generic_applier_for_any_source():
    # Arrange
    registry = ApplierRegistry({("email", ANY_SOURCE): FakeJobApplier})

    # Act
    applier = registry.get("email", "linkedin")

    # Assert
    assert applier is not None
    assert applier.name == "email"


def test_applier_registry_should_prefer_the_platform_specific_applier_over_the_generic_one():
    # Arrange
    registry = ApplierRegistry(
        {
            ("form", ANY_SOURCE): lambda: FakeJobApplier(name="generic"),
            ("form", "gupy"): lambda: FakeJobApplier(name="gupy"),
        }
    )

    # Act
    applier = registry.get("form", "gupy")

    # Assert
    assert applier is not None
    assert applier.name == "gupy"


def test_applier_registry_should_return_none_when_nothing_is_registered_for_the_pair():
    # Arrange
    registry = ApplierRegistry({("email", ANY_SOURCE): FakeJobApplier})

    # Act
    applier = registry.get("form", "manual")

    # Assert
    assert applier is None


def test_applier_registry_should_expose_a_new_platform_when_it_is_registered():
    # Arrange
    registry = ApplierRegistry({})

    # Act
    registry.register("form", "gupy", FakeJobApplier)

    # Assert
    assert ("form", "gupy") in registry.available()
