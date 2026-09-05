.PHONY: install lint format type layers test check clean maildev

install:
	python -m pip install -e ".[dev]"
	pre-commit install || true

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

type:
	mypy

# Enforces the dependency rule between layers (contracts in pyproject.toml).
layers:
	lint-imports

test:
	pytest

# Local SMTP server + web inbox for manual validation of apply-job.
# SMTP on :1025, inbox at http://localhost:1080. Needs `npm install` once.
maildev:
	npx maildev --smtp 1025 --web 1080

# Same gate CI runs. Run it before opening a PR.
check: lint type layers test
	ruff format --check .

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage build dist *.egg-info
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
