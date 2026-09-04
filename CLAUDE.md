# CLAUDE.md

Guidance for any AI agent (and any human) working in this repository.

## What this project is

Deterministic, AI-free CLI scripts (`list-jobs`, `apply-job`). The intelligence lives
*outside*: an orchestrating agent decides and passes data in through flags. Never add an
LLM call, a heuristic guess or a network fetch to the scripts themselves.

## Read before changing code

| Document | What it settles |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Layers, dependency rule, registries |
| [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) | Style, SOLID, error policy, what not to do |
| [docs/TESTING.md](docs/TESTING.md) | AAA pattern, fakes vs mocks, test layout |
| [docs/CONTRACT.md](docs/CONTRACT.md) | CLI input/output — stdout, stderr, exit codes |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | SQLite schema, job ids, dedup, migrations |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch names, commit scopes, PR flow |

## Engineering principles

These are enforced, not aspirational. A PR that breaks one gets changed, not discussed.

### SOLID

One responsibility per class and per file (~200-300 lines is the smell threshold). A new
platform is a **new class plus a registry entry**, never an edit to `application/` or
`domain/`. Use cases depend on a `Protocol` from `domain/ports`, never on a concrete
`infra/` class. Full checklist in
[CODE_STANDARDS.md](docs/CODE_STANDARDS.md#solid--quick-pr-checklist).

### Design patterns in use

| Pattern | Where | Why |
|---|---|---|
| Ports & Adapters | `domain/ports` + `infra/` | swap SQLite or SMTP without touching a use case |
| Registry + Factory | `infra/sources/registry.py` | resolve `--source` by name; Open/Closed for new platforms |
| Strategy | `JobSource`, `JobApplier` | one interchangeable implementation per platform |
| Repository | `JobRepository` | persistence details never leak into `application/` |
| Dependency Injection | use case constructors | `cli/` is the only composition root |
| Decorator | `cli/output.contract_command` | one place turns a typed error into the CLI contract |

Add a pattern only when it removes a real conditional or a real coupling. Speculative
abstraction is a defect here, not foresight.

### Fail-fast

Validate at the boundary and raise immediately. A missing file, an unparseable JSON, a
`--max-length` of `0`, a config with no `storage` mapping — all raise on the spot, with the
value that caused it in the message. Never propagate `None`, an empty default or a silently
truncated value into the next layer, and never let a bad input reach the database or SMTP.

### Exceptions per layer

Each layer raises what it owns and never leaks a lower layer's exception type:

```
infra/         catches sqlite3/json/yaml/smtplib errors → raises a typed JobHunterError
application/   raises JobHunterError for rule violations (InvalidInputError, ...)
domain/        raises ValueError for programming errors that must never happen at runtime
cli/           catches JobHunterError → error JSON on stderr + non-zero exit (contract_command)
```

Rules: every typed error carries the `code` documented in
[CONTRACT.md](docs/CONTRACT.md#errors-any-command); a new code is documented there before it
is raised; always `raise ... from exc` when re-raising; never `except Exception` without
re-raising typed; no stack trace ever reaches stdout or the calling agent.

### EAFP — better to ask forgiveness than permission

Prefer `try/except` over a pre-check that duplicates the operation's own check (`registry`
does `self._factories[name]` inside a `try`, not `if name in ...`). Two exceptions where a
guard is right: a check that produces a *better* error message than the built-in exception,
and any irreversible side effect (sending an email, writing to a database) — look before
you leap there.

## Working agreements

- `make check` green before any commit — it is exactly what CI runs.
- Every change in `domain/`, `application/` or `infra/` ships with its test in the same PR.
- Touching the CLI contract or the data model means updating `CONTRACT.md` / `DATA_MODEL.md`
  in the same PR, plus `CHANGELOG.md` under `Unreleased`.
- Conventional Commits with a mandatory layer scope: `feat(infra): ...`.
- Code, comments and documentation in English. Commit messages in English.
- No `print()` on a command's stdout. `cli/output.py` is the only writer to the streams.
