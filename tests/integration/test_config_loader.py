import pytest

from job_hunter_ai.config.loader import CONFIG_PATH_ENV, load_config, resolve_config_path
from job_hunter_ai.domain.errors import InvalidInputError


def write_config(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_load_config_should_read_the_database_path_from_the_local_file(tmp_path):
    # Arrange
    write_config(
        tmp_path / "config" / "local" / "config.yaml",
        'storage:\n  database_path: "config/local/jobs.db"\n',
    )

    # Act
    config = load_config(root=tmp_path)

    # Assert
    assert config.storage.database_path == tmp_path / "config" / "local" / "jobs.db"


def test_load_config_should_fall_back_to_the_example_when_no_local_file_exists(tmp_path):
    # Arrange
    write_config(
        tmp_path / "config" / "config.example.yaml",
        'storage:\n  database_path: "config/local/jobs.db"\n',
    )

    # Act
    config = load_config(root=tmp_path)

    # Assert
    assert config.storage.database_path.name == "jobs.db"


def test_load_config_should_keep_an_absolute_database_path_untouched(tmp_path):
    # Arrange
    absolute = tmp_path / "elsewhere" / "jobs.db"
    write_config(
        tmp_path / "config" / "local" / "config.yaml",
        f'storage:\n  database_path: "{absolute}"\n',
    )

    # Act
    config = load_config(root=tmp_path)

    # Assert
    assert config.storage.database_path == absolute


def test_load_config_should_use_the_default_path_when_the_storage_section_is_absent(tmp_path):
    # Arrange
    write_config(tmp_path / "config" / "local" / "config.yaml", "candidate:\n  name: Someone\n")

    # Act
    config = load_config(root=tmp_path)

    # Assert
    assert config.storage.database_path == tmp_path / "config" / "local" / "jobs.db"


def test_load_config_should_raise_invalid_input_when_no_configuration_file_exists(tmp_path):
    # Arrange / Act / Assert
    with pytest.raises(InvalidInputError) as error:
        load_config(root=tmp_path)
    assert error.value.code == "INVALID_INPUT"


def test_load_config_should_raise_invalid_input_when_the_yaml_is_malformed(tmp_path):
    # Arrange
    write_config(tmp_path / "config" / "local" / "config.yaml", "storage: [unclosed\n")

    # Act / Assert
    with pytest.raises(InvalidInputError):
        load_config(root=tmp_path)


def test_resolve_config_path_should_prefer_the_environment_override(tmp_path, monkeypatch):
    # Arrange
    override = tmp_path / "custom.yaml"
    monkeypatch.setenv(CONFIG_PATH_ENV, str(override))

    # Act
    resolved = resolve_config_path(tmp_path)

    # Assert
    assert resolved == override
