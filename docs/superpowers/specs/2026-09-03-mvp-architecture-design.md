# JobHunterAi — MVP design (phase 1)

Date: 2026-09-03
Status: Approved

> Historical record of the initial design session. The package layout below was later
> superseded by [ADR-0004](../../adr/0004-single-package.md) (a single `job_hunter_ai`
> package under `src/`); the living reference is [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Purpose

A foundation for automating job applications, designed to be driven by AI agents (local or external). The project provides AI-free CLI scripts — any agent (Claude Code, another LLM, or a human) can orchestrate the decision to apply and call the scripts, passing the data as flags and arguments.

## Core principle

The scripts are **pure and deterministic**. No AI is embedded in the MVP. The "apply or not" decision and the extraction of unstructured data (address, subject) belong to whoever calls the scripts — an external AI agent orchestrating through the CLI. This saves the agent's tokens: mechanical work (sending an email, filling a known form) stays in deterministic code; the AI only decides and extracts what is not structured.

## Guiding user story

> As an AI agent:
> - I want to receive a list of jobs from a source without opening the site by hand.
> - I want to apply to a job I decided matches the profile, in an automated and structured way, passing the data behind my decision as flags and arguments (for the email case). For a fixed, known form, I want a script to fill it for me.
> - That way I save tokens by delegating the automatable work.

## Stack

- **Python** — mature libraries for email (stdlib), CLI (Typer), validation (Pydantic), credentials (python-dotenv), tests (pytest), and future scraping/form filling (Playwright).
- **SQLite** — state and history (collected jobs, application results). Prevents duplicates and re-applications.
- **Local, uncommitted configuration** — each user configures credentials and personal data outside of git.

## Layered architecture

```
job-hunter-ai/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── job.py              # Job
│   │   │   ├── result.py           # ApplicationResult
│   │   │   └── candidate.py        # CandidateProfile, SmtpConfig
│   │   └── ports/
│   │       ├── job_source.py       # JobSource
│   │       ├── job_applier.py      # JobApplier
│   │       └── job_repository.py   # JobRepository
│   ├── application/
│   │   ├── list_jobs.py            # ListJobsUseCase
│   │   └── apply_job.py            # ApplyJobUseCase
│   ├── infra/
│   │   ├── sources/
│   │   │   └── manual_json_source.py   # ManualJsonJobSource (phase 1)
│   │   ├── appliers/
│   │   │   └── email_applier.py        # EmailApplier (phase 1, generic)
│   │   └── repository/
│   │       └── sqlite_repository.py    # SqliteJobRepository
│   ├── config/
│   │   ├── loader.py
│   │   └── templates/
│   │       └── email-body.example.html
│   └── cli/
│       └── main.py                 # Typer app: list-jobs, apply-job
├── config/
│   ├── templates/
│   │   └── email-body.example.html     # versioned
│   ├── config.example.yaml         # versioned
│   └── local/                      # gitignored
│       ├── config.yaml
│       ├── email-body.html         # the user's real version
│       ├── resume.pdf
│       └── sources/
│           └── <platform>.yaml     # per-source settings (non-sensitive), when needed
├── .env.example                    # versioned — credentials/secrets, example
├── .env                            # gitignored — real credentials (SMTP, per-platform logins)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── cli/
└── docs/
```

**Dependency rule**: `cli` → `application` → `domain`. `infra` implements `domain/ports` and is injected into `application` through the constructor. `domain` depends on nothing. Each strategy (source/applier) is a `Protocol`, pluggable through a registry — covering SOLID (Dependency Inversion, Open/Closed).

## Domain entities

```python
# domain/entities/job.py
class Job:
    id: str  # stable hash (source + external_id/url)
    source: str  # "manual", "linkedin", "gupy", ...
    title: str
    company: str
    description: str
    url: str | None
    raw: dict  # original source payload, for auditing
    collected_at: datetime


# domain/entities/result.py
class ApplicationResult:
    job_id: str
    method: Literal["email", "form"]
    status: Literal["sent", "failed", "skipped"]
    applier: str  # "email", "linkedin-form", ...
    detail: str
    applied_at: datetime


# domain/entities/candidate.py
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool


class CandidateProfile:
    name: str
    resume_pdf_path: Path
    smtp: SmtpConfig
    default_subject_template: str
    extra_fields: dict[str, str]  # phone, linkedin_url, portfolio_url... reusable by form appliers
```

## Domain ports

```python
# domain/ports/job_source.py
class JobSource(Protocol):
    def fetch(self, max_length: int, **filters) -> list[Job]: ...


# domain/ports/job_applier.py
class JobApplier(Protocol):
    def apply(self, job: Job, candidate: CandidateProfile, **method_args) -> ApplicationResult: ...


# domain/ports/job_repository.py
class JobRepository(Protocol):
    def save_jobs(self, jobs: list[Job]) -> None: ...
    def save_result(self, result: ApplicationResult) -> None: ...
    def get_job(self, job_id: str) -> Job | None: ...
    def list_results(self, job_id: str | None = None) -> list[ApplicationResult]: ...
```

## Registries (strategy resolution)

- `JobSource`: by `source` (`"manual"` → `ManualJsonJobSource`).
- `JobApplier`: by `(method, source)`. `"email"` has a generic `"*"` fallback (same SMTP, any origin). `"form"` requires a platform-specific applier — with none registered, `apply-job` returns `status="skipped", detail="no form applier for source=X"`.

## CLI (MVP)

```bash
list-jobs  --source manual --file jobs.json --max-length 100
# stdout: JSON list of Job

apply-job  --job-id abc123 --method email --email jobs@company.com --subject "Backend role - David Naves"
# email body and PDF are always fixed (template + local config)

apply-job  --job-id abc123 --method form
# resolves the platform-specific JobApplier through the registry (from the Job's source)

apply-job  --all-ready --method email ...
```

Every command prints JSON on stdout (success) or stderr (a structured error, `{"error": ..., "code": ...}`) with a non-zero exit code — usable by an external agent with no stack trace parsing.

## Static assets (email)

- **Body**: `config/templates/email-body.example.html` versioned (example/starting point) plus `config/local/email-body.html` gitignored (the user's real version, with their own HTML and styling). `EmailApplier` uses the local one when present, falling back to the example. Placeholders (`{{job.title}}`, `{{company}}`, `{{candidate.name}}`...) resolved by a simple engine (Jinja2). Sends multipart (`text/html` plus a text fallback).
- **PDF**: `config/local/resume.pdf` (path configurable in `config.yaml` → `resume_pdf_path`), gitignored — personal data.
- **Subject**: comes from the `--subject` flag of whoever calls `apply-job` (phase 1); when omitted, uses `default_subject_template` from the local config.

## Configuration vs credentials

An explicit split between configuration (non-sensitive) and credentials (secret) — never in the same file:

- `config/local/config.yaml`: general non-sensitive settings (name, `resume_pdf_path`, `default_subject_template`, `preferred_apply_order`, `extra_fields`) — becomes `CandidateProfile`, reusable by any applier.
- `.env` (root, gitignored): credentials and secrets — SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`) and per-platform logins (`LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`, ...), loaded through `python-dotenv`. Populates `SmtpConfig` and the form appliers' credentials.
- `.env.example`: versioned, listing the expected keys with no real values.
- `config/local/sources/<name>.yaml`: non-sensitive per-platform settings (selectors, timeouts, field mapping), loaded only by the matching `infra/appliers/<name>_form_applier.py` — the domain stays platform-agnostic. That platform's credentials live in `.env`, not here.
- `config/config.example.yaml`: versioned configuration template with no real data.

`config/loader.py` combines `.env` and `config.yaml` into a single `CandidateProfile`.

## Errors

Use cases never let a raw exception leak to the CLI. `infra` raises typed exceptions (`SmtpError`, `SourceNotFoundError`, `ApplierNotFoundError`); `application`/`cli` catch them and convert them into structured error JSON plus a non-zero exit code.

## Tests

- The AAA pattern (Arrange/Act/Assert) in every test, with `pytest`.
- `tests/unit/`: use cases with mocked ports (fake `JobSource`/`JobApplier`), pure entities.
- `tests/integration/`: a real `SqliteJobRepository` (temp database), `EmailApplier` against a fake SMTP server (local `aiosmtpd`).
- `tests/cli/`: Typer commands through `CliRunner`, checking the output JSON and the exit code.
- Every new piece of code in `application/`, `domain/` or `infra/` requires a test before merge.

## Out of the MVP scope (phase 2+)

- `enrich-job`/`decide-job` as their own scripts, or a formal `ai/` layer — deciding and extracting unstructured data belong to the external orchestrating agent for now.
- `ApplyInfo`/`ApplicationDecision` as domain entities — to be revisited if and when an AI layer is formalized inside the project.
- Automated sources (LinkedIn scraper, Gupy, etc.) — phase 1 has only `ManualJsonJobSource`.
- Per-platform form `JobApplier` implementations — added as each platform is supported.
- Multiple resumes selectable per job — phase 1 uses a single fixed resume.
