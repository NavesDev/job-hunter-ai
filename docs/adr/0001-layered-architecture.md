# ADR-0001: Layered architecture with ports and registries

- **Status:** Accepted
- **Date:** 2026-09-03
- **Deciders:** NavesDev

## Context

The project will integrate N job platforms (manual, LinkedIn, Gupy, Indeed...), each with its own listing format and its own application method. Without isolation, every new platform would spread `if source == ...` across the whole codebase.

## Decision

Layers `cli/ → application/ → domain/ ← infra/`. Contracts are `Protocol` definitions in `domain/ports` (`JobSource`, `JobApplier`, `JobRepository`); concrete implementations live in `infra/` and are resolved by a registry in the `cli/` layer.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Flat scripts, one file per command | Duplicates business rules for every new platform; no isolated place to test |
| Abstract base classes (`ABC`) instead of `Protocol` | Couples `infra/` to `domain/` through inheritance; `Protocol` gives structural typing without a mandatory import |
| A plugin framework (entry points) | Unnecessary complexity with a single source in phase 1 |

## Consequences

**Positive:** a new platform means a new class in `infra/` plus its registration, with no changes to `application`/`domain` (Open/Closed). Use cases are testable with fakes, without I/O.

**Negative / accepted cost:** more files and indirection than a single script would need for the MVP.
