# job-hunter-ai

[![CI](https://github.com/NavesDev/job-hunter-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/NavesDev/job-hunter-ai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230)](https://docs.astral.sh/ruff/)

🤖 A foundation for automating job applications, designed to be driven by AI agents (local or external).

The CLI scripts are **pure and AI-free**: any agent (Claude Code, another LLM, or a human) orchestrates from the outside — deciding whether to apply and with which data — and calls the scripts through flags and arguments. The mechanical work (sending an email, filling a known form) stays in deterministic code.

Docs: [Architecture](docs/ARCHITECTURE.md) · [Features](docs/FEATURES.md) · [Current sprint](docs/sprints/SPRINT-01-MVP.md) · [CLI contract](docs/CONTRACT.md) · [Data model](docs/DATA_MODEL.md) · [Code standards](docs/CODE_STANDARDS.md) · [Testing standards](docs/TESTING.md) · [ADRs](docs/adr/README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Status

🚧 **Pre-alpha.** `list-jobs` works end to end with the `manual` source: it normalizes a JSON file, stores the jobs in SQLite and prints the contract payload. `apply-job` still answers `NOT_IMPLEMENTED` — it is the remaining half of [Sprint 01](docs/sprints/SPRINT-01-MVP.md).

## Requirements

Python 3.11+.

## Installation

```bash
git clone git@github.com:NavesDev/job-hunter-ai.git
cd job-hunter-ai
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp config/config.example.yaml config/local/config.yaml
cp config/templates/email-body.example.html config/local/email-body.html
cp .env.example .env
# edit config/local/config.yaml with non-sensitive settings (name, resume, preferences)
# edit .env with credentials (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, ...)
# customize config/local/email-body.html (free-form HTML, your own styling)
# drop your resume at config/local/resume.pdf (or point elsewhere in config.yaml)
```

`config/local/` and `.env` are gitignored. Non-sensitive settings (name, paths, preferences) live in `config/local/config.yaml`; credentials and secrets (SMTP, per-platform logins) live in `.env` — never in the YAML, never committed. Use a dedicated **app password**, never your account's main password (see [SECURITY.md](SECURITY.md)).

## Usage

### List jobs

```bash
list-jobs --source manual --file jobs.json --max-length 100
```

| Flag | Required | Description |
|---|---|---|
| `--source` | yes | Registered job source (`manual` in phase 1) |
| `--file` | source-dependent | Path to the input JSON/CSV (`manual` source) |
| `--max-length` | no (default 50) | Maximum number of jobs returned |

The `manual` source expects a JSON list; `title` and `company` are required, everything else optional:

```json
[
  {"title": "Backend Engineer", "company": "Acme", "url": "https://acme.com/jobs/1",
   "description": "Python, SQL", "apply_email": "jobs@acme.com"}
]
```

Output: JSON on stdout, a list of normalized jobs (`id`, `source`, `title`, `company`, `description`, `url`, `apply_email`, `raw`, `collected_at`). Every run stores and deduplicates into the local SQLite database — stable ids, no duplicates across runs ([DATA_MODEL.md](docs/DATA_MODEL.md)). Errors go to stderr as `{"error": ..., "code": ...}` with a non-zero exit code ([CONTRACT.md](docs/CONTRACT.md)).

### Apply to a job

```bash
apply-job --job-id abc123 --method email --email jobs@company.com --subject "Backend role - Your Name"
apply-job --job-id abc123 --method form
apply-job --all-ready --method email
```

| Flag | Required | Description |
|---|---|---|
| `--job-id` | yes (or `--all-ready`) | Job id returned by `list-jobs` |
| `--method` | yes | `email` or `form` |
| `--email` | if `method=email` and the job carries no email | Destination address |
| `--subject` | no | Email subject; falls back to the configured default |
| `--all-ready` | no | Applies in batch to every job already collected |

The email body (`config/local/email-body.html`, falling back to `config/templates/email-body.example.html`) and the resume PDF (`config/local/resume.pdf`) are always fixed — only the method, the address and the subject vary per call. `--method form` needs an applier registered for the job's platform; without one it returns `status=skipped` instead of blocking the rest of the flow.

### Output and errors

Every command prints structured JSON. Success goes to stdout; failures go to stderr with a non-zero exit code:

```json
{"error": "smtp connection refused", "code": "SMTP_ERROR"}
```

This lets an external agent (AI or human) parse the result without depending on stack traces. Full contract in [docs/CONTRACT.md](docs/CONTRACT.md).

## Architecture at a glance

```
cli/  →  application/  →  domain/
                              ↑
                           infra/ (implements domain/ports)
```

Every job source (`JobSource`) and every application method (`JobApplier`) is a pluggable strategy resolved through a registry — a new platform lands in `infra/` without touching `application`/`domain`. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); decisions in [docs/adr/](docs/adr/README.md).

## Development

```bash
pip install -e ".[dev]"
make check     # ruff + ruff format --check + mypy + import-linter + pytest (same gate as CI)
```

The dependency rule between layers is enforced, not just documented: `import-linter` contracts declared in `pyproject.toml` fail the build if `application/` ever imports `infra/`, or if anything leaks into `domain/`.

Tests follow the **AAA** pattern (Arrange/Act/Assert, spelled out in comments). Every new piece of code in `domain/`, `application/` or `infra/` needs a test before merge. See [docs/TESTING.md](docs/TESTING.md), [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

This is job application automation. Whoever runs it is responsible for how it is used:

- **Terms of Service.** Job platforms (LinkedIn, Gupy, Indeed and others) restrict or forbid automated collection and account automation. This project ships no scraper for any platform; every new source must be checked against the site's ToS before being implemented and used.
- **No bulk blasting.** The tool is meant for personal applications, one at a time. Do not use it for mass sending — it is bad for the people receiving it and may qualify as spam.
- **Truthful data.** The resume and profile you send must be yours and accurate.
- **Personal data.** Your resume, history and credentials stay on your machine, in gitignored files. The project sends nothing to any third-party service.
- **Human review.** Automation sends exactly what you configured; check the email body and the recipient before applying in batch.

The project is provided "as is", without warranty, under the [MIT license](LICENSE).

## Roadmap

Current and planned deliverables in [docs/FEATURES.md](docs/FEATURES.md). Sprint in progress in [docs/sprints/SPRINT-01-MVP.md](docs/sprints/SPRINT-01-MVP.md). History in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
