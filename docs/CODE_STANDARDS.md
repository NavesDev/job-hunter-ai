# Code standards

## Style

- **PEP 8**, enforced by `ruff` (lint + format, configured in `pyproject.toml`, 100-column lines). No style debates in a PR — if the linter accepts it, it is accepted.
- **Type hints are mandatory** on every public function and method. `mypy` runs in `strict` mode in CI.
- `make check` runs the whole gate (lint + format + types + tests) — the same thing CI executes.
- File/module names: `snake_case`. Classes: `PascalCase`. Functions and variables: `snake_case`. Constants: `UPPER_SNAKE_CASE`.
- Docstrings only where the name does not make the *why* obvious (do not restate the *what* that the type hints already show).
- Code, comments, docstrings and documentation are written in English.

## Architecture (dependency rule)

```
cli/  →  application/  →  domain/
                              ↑
                           infra/
```

- `domain/` never imports from `application/`, `infra/` or `cli/`. Zero external dependencies (not even Pydantic, if avoidable — plain `dataclass`).
- `application/` depends on `domain/` (ports) only. It never imports a concrete class from `infra/` — those always arrive through constructor injection.
- `infra/` implements `domain/ports`. It may depend on external libraries (SQLite, SMTP, Playwright).
- `cli/` is the only place that knows how to assemble the concrete dependency graph (registry/factory) and instantiate use cases.

The layers live under the single `src/job_hunter_ai/` package ([ADR-0004](adr/0004-single-package.md)); imports are always absolute and explicit (`from job_hunter_ai.domain.ports import JobSource`).

Common violation to avoid: a use case importing `job_hunter_ai.infra.appliers.email_applier` directly instead of receiving a `JobApplier` in its constructor — that breaks testability and Dependency Inversion.

**The rule is enforced, not just documented.** `import-linter` checks four contracts declared in `pyproject.toml`, and CI fails when one breaks:

| Contract | What it forbids |
|---|---|
| `domain depends on nothing` | `domain/` importing `application/`, `infra/`, `config/` or `cli/` |
| `application receives ports by injection` | `application/` importing `infra/` or `cli/` |
| `infra implements ports` | `infra/` importing `application/` or `cli/` |
| `domain stays free of third-party dependencies` | `domain/` importing `typer`, `yaml`, `dotenv` or `sqlite3` |

Run it locally with `make layers` (or `lint-imports`); `make check` already includes it. Adding a layer or a port means adding or updating a contract in the same PR.

## SOLID — quick PR checklist

- **S**: does the class do exactly one thing? If its name contains "and"/"or" (`SourceAndApplier`), probably not.
- **O**: is a new platform/source an extension (new class plus registration) rather than an edit of existing code?
- **L**: can any `JobSource`/`JobApplier` implementation replace another without breaking its callers?
- **I**: does the port avoid forcing an implementation to provide a method that makes no sense for it?
- **D**: does `application/` depend on a `Protocol` rather than a concrete `infra/` class?

## Design patterns in use

Every pattern below exists to remove a concrete conditional or a concrete coupling. Adding one "for flexibility", with no second implementation in sight, is a defect — not foresight.

| Pattern | Where | What it buys |
|---|---|---|
| Ports & Adapters | `domain/ports` + `infra/` | swapping SQLite or SMTP without touching a use case |
| Registry + Factory | `infra/sources/registry.py` | resolving `--source` by name; a new platform is a new entry, not an edit |
| Strategy | `JobSource`, `JobApplier` | one interchangeable implementation per platform |
| Repository | `JobRepository` | persistence details never leak into `application/` |
| Dependency Injection | use case constructors | `cli/` is the single composition root |
| Decorator | `cli/output.contract_command` | one place turns a typed error into the CLI contract |

## Fail-fast

Validate at the boundary and raise immediately, with the offending value in the message.

- A missing `--file`, an unparseable JSON, a `--max-length` of `0`, a config with no `storage` mapping: all raise where they are read.
- Never propagate a `None`, an empty default or a silently truncated value into the next layer.
- Never let an invalid input reach the database or the SMTP server — an external side effect is the last place to discover a bad argument.
- A precondition that can only be broken by a bug (a `Job` with no natural key) raises `ValueError` from `domain/`, not a contract error: it is not a runtime condition the calling agent can fix.

## Exceptions per layer

Each layer raises what it owns, and never leaks a lower layer's exception type upwards:

```
infra/         catches sqlite3 / json / yaml / smtplib errors → raises a typed JobHunterError
application/   raises JobHunterError for rule violations (InvalidInputError, ...)
domain/        raises ValueError for programming errors that must never happen at runtime
cli/           catches JobHunterError → error JSON on stderr + non-zero exit (contract_command)
```

Rules:

- Every typed error carries the `code` documented in [CONTRACT.md](CONTRACT.md#errors-any-command). A new code is documented there **before** it is raised.
- Always chain the cause when re-raising: `raise InvalidInputError(...) from exc`.
- `cli/output.contract_command` is the only boundary that converts an exception into an exit code — a command body never formats an error itself.
- No stack trace ever reaches stdout or the calling agent.

## EAFP — better to ask forgiveness than permission

Prefer `try/except` over a pre-check that just duplicates the operation's own check:

```python
# Yes — one lookup, the failure path carries the message
try:
    factory = self._factories[name]
except KeyError as exc:
    raise SourceNotFoundError(f"unknown source `{name}`") from exc

# No — two lookups, and a race between the check and the use
if name in self._factories:
    factory = self._factories[name]
```

Two cases where looking before you leap is the right call:

1. The guard produces a **better message** than the built-in exception would (`f"input file not found: {path}"` beats a raw `FileNotFoundError`).
2. The operation has an **irreversible side effect** (sending an email, writing to the database). There, validate first — an exception after the fact does not un-send anything.

## File and unit size

A file growing too large (~200-300 lines for an ordinary module) signals mixed responsibilities — split it before piling on more. Prefer many small, cohesive files over a few big ones (the same principle already applied in `domain/entities/` and `domain/ports/`, one file per concept).

## Commits

Conventional Commits **with a mandatory layer scope**: `feat(infra): ...`, `fix(cli): ...`, `test(application): ...`. The list of valid scopes and the branch pattern (`type/issue-id-description`) are in [CONTRIBUTING.md](../CONTRIBUTING.md#commits). The body explains the *why* whenever the diff does not make it obvious.

## What not to do

- No stray `print()`/log on a CLI command's `stdout` — it breaks the [contract](CONTRACT.md).
- No blanket exception (`except Exception`) swallowing an error without logging or re-raising it typed.
- No business logic in `cli/` — the CLI only parses flags, resolves dependencies, calls the use case and formats the output.
- No direct file or network access in `domain/` or `application/`.
