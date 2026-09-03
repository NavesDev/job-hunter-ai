import json
from typing import Any

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def parse_stderr_json(result: Any) -> dict[str, Any]:
    """Read the error JSON from stderr, tolerating click versions that merge the streams."""
    raw = result.stderr if result.stderr else result.output
    parsed: dict[str, Any] = json.loads(raw.strip().splitlines()[-1])
    return parsed
