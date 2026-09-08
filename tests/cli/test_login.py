"""The `login` command's contract: JSON on stdout, typed error JSON on stderr."""

import json

import pytest

from job_hunter_ai.cli.main import login_app
from tests.cli.conftest import parse_stderr_json


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """An isolated root whose `.env` carries a made-up GeekHunter credential."""
    monkeypatch.chdir(tmp_path)
    for name in ("GEEKHUNTER_USERNAME", "GEEKHUNTER_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_login_should_fail_with_source_not_found_when_the_platform_has_no_strategy(
    runner, workspace
):
    # Arrange
    args = ["--source", "manual"]

    # Act
    result = runner.invoke(login_app, args)

    # Assert
    assert result.exit_code != 0
    assert parse_stderr_json(result)["code"] == "SOURCE_NOT_FOUND"


def test_login_should_fail_with_invalid_input_when_the_credentials_are_missing(runner, workspace):
    # Arrange
    args = ["--source", "geekhunter"]

    # Act
    result = runner.invoke(login_app, args)

    # Assert
    assert result.exit_code != 0
    error = parse_stderr_json(result)
    assert error["code"] == "INVALID_INPUT"
    assert "GEEKHUNTER_USERNAME" in error["error"]


def test_login_should_never_print_the_password_when_it_fails(runner, workspace):
    # Arrange
    (workspace / ".env").write_text(
        "GEEKHUNTER_USERNAME=ada@example.com\nGEEKHUNTER_PASSWORD=s3cr3t\n", encoding="utf-8"
    )
    (workspace / "config" / "local" / "sources").mkdir(parents=True)
    (workspace / "config" / "local" / "sources" / "geekhunter.yaml").write_text(
        'base_url: "http://127.0.0.1:1"\n'  # nothing listens there: the sign-in cannot happen
        f'browser_profile_dir: "{workspace / "profile"}"\n'
        "timeout_ms: 3000\n",
        encoding="utf-8",
    )

    # Act
    result = runner.invoke(login_app, ["--source", "geekhunter"])

    # Assert
    assert result.exit_code != 0
    raw = result.stderr if result.stderr else result.output
    assert "s3cr3t" not in raw
    assert json.loads(raw.strip().splitlines()[-1])["code"] == "SESSION_ERROR"
