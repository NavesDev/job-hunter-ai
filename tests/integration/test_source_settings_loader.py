"""Per-platform, non-sensitive settings: `config/local/sources/<platform>.yaml`."""

import pytest

from job_hunter_ai.config.sources import load_source_settings
from job_hunter_ai.domain.errors import InvalidInputError


def write_settings(root, name, body):
    path = root / "config" / "local" / "sources" / f"{name}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_load_source_settings_should_return_the_mapping_when_the_file_exists(tmp_path):
    # Arrange
    write_settings(tmp_path, "geekhunter", 'filters:\n  workModality: "remote"\n')

    # Act
    settings = load_source_settings("geekhunter", root=tmp_path)

    # Assert
    assert settings == {"filters": {"workModality": "remote"}}


def test_load_source_settings_should_return_nothing_when_the_platform_has_no_file(tmp_path):
    # Act
    settings = load_source_settings("geekhunter", root=tmp_path)

    # Assert
    assert settings == {}


def test_load_source_settings_should_raise_invalid_input_when_the_yaml_is_malformed(tmp_path):
    # Arrange
    write_settings(tmp_path, "geekhunter", "filters: [unclosed\n")

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        load_source_settings("geekhunter", root=tmp_path)
    assert "geekhunter.yaml" in str(error.value)


def test_load_source_settings_should_raise_invalid_input_when_the_top_level_is_not_a_mapping(
    tmp_path,
):
    # Arrange
    write_settings(tmp_path, "geekhunter", "- remote\n- hybrid\n")

    # Act / Assert
    with pytest.raises(InvalidInputError):
        load_source_settings("geekhunter", root=tmp_path)
