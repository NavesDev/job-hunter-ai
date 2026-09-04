import pytest

from job_hunter_ai.config.credentials import DEFAULT_PORT, load_smtp_config
from job_hunter_ai.domain.errors import InvalidInputError

REQUIRED = {
    "SMTP_HOST": "smtp.example.com",
    "SMTP_USERNAME": "ada@example.com",
    "SMTP_PASSWORD": "app-password",
}


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_USE_TLS"):
        monkeypatch.delenv(name, raising=False)


def test_load_smtp_config_should_read_every_setting_from_the_env_file(tmp_path):
    # Arrange
    (tmp_path / ".env").write_text(
        "SMTP_HOST=smtp.example.com\nSMTP_PORT=2525\n"
        "SMTP_USERNAME=ada@example.com\nSMTP_PASSWORD=app-password\nSMTP_USE_TLS=false\n",
        encoding="utf-8",
    )

    # Act
    config = load_smtp_config(root=tmp_path)

    # Assert
    assert config.host == "smtp.example.com"
    assert config.port == 2525
    assert config.username == "ada@example.com"
    assert config.use_tls is False


def test_load_smtp_config_should_default_the_port_and_tls_when_they_are_absent(
    tmp_path, monkeypatch
):
    # Arrange
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)

    # Act
    config = load_smtp_config(root=tmp_path)

    # Assert
    assert config.port == DEFAULT_PORT
    assert config.use_tls is True


def test_load_smtp_config_should_raise_invalid_input_when_a_credential_is_missing(
    tmp_path, monkeypatch
):
    # Arrange
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")

    # Act / Assert
    with pytest.raises(InvalidInputError) as error:
        load_smtp_config(root=tmp_path)
    assert error.value.code == "INVALID_INPUT"
    assert "SMTP_USERNAME" in str(error.value)


def test_load_smtp_config_should_raise_invalid_input_when_the_port_is_not_a_number(
    tmp_path, monkeypatch
):
    # Arrange
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SMTP_PORT", "not-a-port")

    # Act / Assert
    with pytest.raises(InvalidInputError):
        load_smtp_config(root=tmp_path)


def test_load_smtp_config_should_not_put_the_password_in_the_error_when_it_is_missing(
    tmp_path, monkeypatch
):
    # Arrange
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USERNAME", "ada@example.com")

    # Act
    with pytest.raises(InvalidInputError) as error:
        load_smtp_config(root=tmp_path)

    # Assert
    assert "SMTP_PASSWORD" in str(error.value)
    assert "app-password" not in str(error.value)
