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

## SOLID — quick PR checklist

- **S**: does the class do exactly one thing? If its name contains "and"/"or" (`SourceAndApplier`), probably not.
- **O**: is a new platform/source an extension (new class plus registration) rather than an edit of existing code?
- **L**: can any `JobSource`/`JobApplier` implementation replace another without breaking its callers?
- **I**: does the port avoid forcing an implementation to provide a method that makes no sense for it?
- **D**: does `application/` depend on a `Protocol` rather than a concrete `infra/` class?

## File and unit size

A file growing too large (~200-300 lines for an ordinary module) signals mixed responsibilities — split it before piling on more. Prefer many small, cohesive files over a few big ones (the same principle already applied in `domain/entities/` and `domain/ports/`, one file per concept).

## Commits

Conventional Commits **with a mandatory layer scope**: `feat(infra): ...`, `fix(cli): ...`, `test(application): ...`. The list of valid scopes and the branch pattern (`type/issue-id-description`) are in [CONTRIBUTING.md](../CONTRIBUTING.md#commits). The body explains the *why* whenever the diff does not make it obvious.

## What not to do

- No stray `print()`/log on a CLI command's `stdout` — it breaks the [contract](CONTRACT.md).
- No blanket exception (`except Exception`) swallowing an error without logging or re-raising it typed.
- No business logic in `cli/` — the CLI only parses flags, resolves dependencies, calls the use case and formats the output.
- No direct file or network access in `domain/` or `application/`.
