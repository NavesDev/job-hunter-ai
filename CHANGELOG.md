# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project follows [SemVer](https://semver.org/) starting from the first release.

## [Unreleased]

### Added

- `list-jobs --source manual --file jobs.json`: reads a JSON file, normalizes it into `Job`s, stores them in SQLite and prints the contract payload on stdout ([TASK-01](docs/sprints/SPRINT-01-MVP.md)).
- Deterministic job ids (`domain/job_id.py`) following [DATA_MODEL.md](docs/DATA_MODEL.md#job-identity): running `list-jobs` twice over the same input yields the same ids, no duplicated rows, and the original `collected_at` is preserved.
- `SqliteJobRepository` with versioned SQL migrations applied on open — the database is created on first run at `storage.database_path`.
- `SourceRegistry`: resolves `--source` by name and fails with `SOURCE_NOT_FOUND` for an unknown platform. A new source is a new class plus one entry.
- `config/loader.py`: typed non-sensitive configuration from `config/local/config.yaml`, falling back to the versioned example; `$JOB_HUNTER_AI_CONFIG` overrides the path.
- `cli/output.contract_command`: the single boundary turning a typed domain error into the contract's error JSON plus a non-zero exit code.
- `CLAUDE.md`: engineering principles for agents working in the repository — SOLID, patterns in use, fail-fast, exceptions per layer, EAFP.

- Installable `job-hunter-ai` package (`pyproject.toml`, `src/` layout) exposing the `list-jobs` and `apply-job` entrypoints.
- Domain entities and ports (`Job`, `ApplicationResult`, `CandidateProfile`, `SmtpConfig`, `JobSource`, `JobApplier`, `JobRepository`) plus typed errors carrying the CLI contract `code`.
- CLI skeleton: both commands exist, validate the contract flags and answer `NOT_IMPLEMENTED` until [Sprint 01](docs/sprints/SPRINT-01-MVP.md) delivers them.
- Versioned example configuration: `config/config.example.yaml` and `config/templates/email-body.example.html`.
- Quality gate: GitHub Actions CI (Python 3.11 and 3.12), `.pre-commit-config.yaml`, `Makefile` (`make check`) and `.editorconfig`.
- Layer enforcement: `import-linter` contracts in `pyproject.toml` fail the build when the dependency rule is inverted (`make layers`), covering the boundaries between `domain`, `application`, `infra` and `cli`, plus keeping `domain` free of third-party imports.
- Initial test suite (`pytest`, AAA pattern) covering entities, errors and the CLI output contract.
- `SECURITY.md` with a reporting policy and threat model, `CODE_OF_CONDUCT.md`, issue and pull request templates.
- ADRs under `docs/adr/` (layered architecture, CLI as a JSON contract, config/credentials split, single package).
- `docs/DATA_MODEL.md`: SQLite schema, job id rule, deduplication, idempotency and migrations.
- `docs/sprints/SPRINT-01-MVP.md`: MVP sprint with two deliverables — listing jobs from a manual source and applying by email.
- *Responsible use* section in the README (platform Terms of Service, volume, personal data).

### Changed

- `docs/CODE_STANDARDS.md` now states the enforced principles: design patterns in use, fail-fast, exceptions per layer and EAFP.
- `docs/CONTRACT.md`: the `list-jobs` payload documents `apply_email` and the nullability of each field; `--max-length` must be `>= 1`.

- Layers now live under the single `src/job_hunter_ai/` package instead of top-level packages (`domain/`, `config/`), avoiding namespace collisions — [ADR-0004](docs/adr/0004-single-package.md).
- `docs/FEATURES.md` rewritten around delivered value rather than classes and modules.
- `CONTRIBUTING.md`: mandatory layer scope in commits (`feat(infra): ...`) and the `type/issue-id-description` branch pattern.
- Documentation and commit messages standardized in English.

### Documentation

- Layered architecture (`domain`/`application`/`infra`/`cli`) documented in `docs/ARCHITECTURE.md`.
- Full MVP design in `docs/superpowers/specs/2026-09-03-mvp-architecture-design.md`.
- CLI input/output contract (`list-jobs`, `apply-job`) in `docs/CONTRACT.md`.
- Code standards (SOLID, dependency rule, style) in `docs/CODE_STANDARDS.md`.
- Testing standards (AAA, unit/integration/cli) in `docs/TESTING.md`.
- README with installation, flags and usage examples.
- Credentials (`.env`) separated from configuration (`config/local/config.yaml`).

[Unreleased]: https://github.com/NavesDev/job-hunter-ai/commits/main
