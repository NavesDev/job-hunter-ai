# Architecture

Living reference for the project's architecture. Decisions are recorded in [docs/adr/](adr/README.md); the original design discussion lives in [docs/superpowers/specs/2026-09-03-mvp-architecture-design.md](superpowers/specs/2026-09-03-mvp-architecture-design.md). Database schema, job ids and idempotency are in [DATA_MODEL.md](DATA_MODEL.md).

## Core principle

The scripts are **pure, deterministic and AI-free**. Any agent (Claude Code, another LLM, or a human) orchestrates from the outside, calling the scripts through the CLI and passing decision data as flags and arguments. Mechanical work (sending an email, filling a known form) stays in code; the AI only decides and extracts unstructured data — which saves the agent's tokens.

## Layers

```
cli/  →  application/  →  domain/
                              ↑
                           infra/ (implements domain/ports)
```

- **domain/**: entities and contracts (`Protocol`), zero external dependencies.
- **application/**: use cases, orchestrating the domain through ports injected in the constructor. No direct I/O.
- **infra/**: concrete implementations (SQLite, SMTP, job sources). Implements `domain/ports`.
- **cli/**: entrypoint (Typer). Resolves concrete dependencies through a registry, calls the use case, prints JSON.

Every pluggable strategy (job source, application method) is a `Protocol` in `domain/ports` resolved by a **registry** — a new platform means a new class in `infra/`, with no changes to `application`/`domain` (Open/Closed, Dependency Inversion).

The arrows above are enforced by `import-linter` contracts declared in `pyproject.toml` and checked by CI (`make layers`) — an import that inverts one of them fails the build. See [CODE_STANDARDS.md](CODE_STANDARDS.md#architecture-dependency-rule) for the contract list.

## Folder layout

A single distributable package (`job_hunter_ai`) under `src/`, with the layers as subpackages — see [ADR-0004](adr/0004-single-package.md).

```
src/job_hunter_ai/
├── domain/
│   ├── entities/    Job, ApplicationResult, CandidateProfile, SmtpConfig
│   ├── ports/       JobSource, JobApplier, ApplierRegistry, JobRepository
│   ├── job_id.py    the deterministic job identity rule
│   ├── time_utils.py  ISO 8601 UTC, the single time representation
│   └── errors.py    typed exceptions, each carrying its contract `code`
├── application/     ListJobsUseCase, ApplyJobUseCase
├── infra/
│   ├── sources/     concrete JobSource (ManualJsonJobSource) + registry
│   ├── appliers/    EmailApplier + email_message builder + registry
│   └── repository/  SqliteJobRepository + migrations_runner + migrations/
├── config/
│   ├── loader.py       non-sensitive settings from config/local/config.yaml
│   └── credentials.py  SMTP credentials, only from .env
└── cli/
    ├── main.py      list-jobs, apply-job
    ├── dependencies.py  the composition root (lazy factories)
    ├── serializers.py  entities → the JSON payloads of CONTRACT.md
    └── output.py    the only place that writes to stdout/stderr

config/
├── templates/email-body.example.html   versioned (example)
├── config.example.yaml                 versioned (example) — non-sensitive settings
└── local/                              gitignored: config.yaml, email-body.html, resume.pdf, sources/<platform>.yaml

.env.example                            versioned (example) — credentials and secrets
.env                                    gitignored — real credentials (SMTP, per-platform logins)

tests/
├── unit/         use cases with faked ports
├── fakes/        in-memory port implementations shared by the suites
├── integration/  real SQLite, local fake SMTP (aiosmtpd)
└── cli/          Typer CliRunner
```

## Registries (strategy resolution)

| Port | Resolution key | Phase 1 | Extension |
|---|---|---|---|
| `JobSource` | `source` | `"manual"` | one new source per platform |
| `JobApplier` | `(method, source)` | `"email" → "*"` (generic) | `"form" → <platform>`, mandatory per site |

With no applier registered for `(method, source)`, `apply-job` returns `status="skipped"` — never a silent failure, never a blocked flow.

## Configuration vs credentials

Two distinct things, two distinct places:

- **Configuration** (non-sensitive: paths, default template, preferred method order): `config/local/config.yaml`, loaded by `config/loader.py`.
- **Credentials** (secret: SMTP username/password, per-platform logins/tokens): `.env` at the root, loaded through `python-dotenv`. Never committed, never in YAML.

`config/loader.py` assembles `CandidateProfile` from the YAML; `config/credentials.py` assembles `SmtpConfig` from `.env`, and is only called when a command actually needs to send something. Platform-specific credentials use a per-source prefix (`LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`) in the same `.env` — `config/local/sources/<platform>.yaml` only holds that platform's non-sensitive settings (selectors, timeouts), when needed.

## Main contracts

Full detail in the [spec](superpowers/specs/2026-09-03-mvp-architecture-design.md#domain-entities). Summary:

- `Job` — a normalized job posting, independent of its origin.
- `ApplicationResult` — the outcome of an application attempt (`sent`/`failed`/`skipped`).
- `CandidateProfile` — the candidate's profile (local config), including a generic `extra_fields` reusable by form appliers of any platform.

## Errors

`infra` raises typed exceptions (`domain/errors.py`, each carrying a `code` from the [contract](CONTRACT.md)); the `contract_command` decorator in `cli/output.py` catches them at the single boundary and turns them into structured JSON on stderr plus a non-zero exit code. No raw stack trace ever reaches the agent that called the script. The full policy — fail-fast, which layer raises what, and when EAFP applies — is in [CODE_STANDARDS.md](CODE_STANDARDS.md#fail-fast).

## Tests

AAA (Arrange/Act/Assert) is mandatory. `pytest`. Every new piece of code in `domain/`, `application/` or `infra/` requires a test before merge.

## Out of the current scope

The "apply or not" decision and unstructured data extraction (pulling an address or subject out of a description) have no script or layer of their own for now — they belong to the external orchestrating agent. See [Features](FEATURES.md) for status and evolution.
