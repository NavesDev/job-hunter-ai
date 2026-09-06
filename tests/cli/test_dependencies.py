"""The composition root is the only place that knows where settings come from."""

import pytest

from job_hunter_ai.cli.dependencies import build_source_registry
from job_hunter_ai.domain.errors import InvalidInputError


def write_geekhunter_settings(root, body):
    path = root / "config" / "local" / "sources" / "geekhunter.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_build_source_registry_should_hand_the_platform_settings_to_geekhunter(tmp_path):
    # Arrange
    write_geekhunter_settings(tmp_path, 'filters:\n  workModality: "sometimes-remote"\n')

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        build_source_registry(tmp_path).get("geekhunter")
    assert "sometimes-remote" in str(error.value)


def test_build_source_registry_should_build_geekhunter_when_the_platform_has_no_settings(tmp_path):
    # Act
    source = build_source_registry(tmp_path).get("geekhunter")

    # Assert
    assert source.name == "geekhunter"
