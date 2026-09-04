# ADR-0004: A single `job_hunter_ai` package under `src/`

- **Status:** Accepted
- **Date:** 2026-09-03
- **Deciders:** NavesDev

## Context

The initial design placed `src/domain/`, `src/application/`, `src/infra/` and `src/cli/` as top-level packages. Once installed, those names would occupy the Python environment's global namespace — `import config` or `import domain` would collide with any other installed library.

## Decision

A single distributable package, `src/job_hunter_ai/`, with the layers as subpackages: `job_hunter_ai/{domain,application,infra,config,cli}`. A `src/` layout (not flat), declared through `[tool.setuptools.packages.find] where = ["src"]`.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Top-level packages (`domain`, `infra`, `config`) | Name collision in `site-packages`; `config` is especially common |
| A flat layout (no `src/`) | Tests import from the working directory instead of the installed package, hiding packaging mistakes |
| Several distributable packages | Versioning overhead with no gain — the layers always version together |

## Consequences

**Positive:** explicit imports (`from job_hunter_ai.domain.ports import JobSource`), with no collisions. `pip install -e .` exercises the same import path the end user gets.

**Negative / accepted cost:** longer import paths; the earlier documentation referring to `src/domain/` had to be updated.
