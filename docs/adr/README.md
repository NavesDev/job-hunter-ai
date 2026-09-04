# Architecture Decision Records

Any architectural decision that changes a layer, a port, a contract or a dependency becomes an ADR here — before it is implemented.

## How to use it

1. Copy [`0000-template.md`](0000-template.md) to `NNNN-title-in-kebab-case.md`, where `NNNN` is the next free number.
2. Fill it in and open a PR with a `docs(adr): ...` commit.
3. An accepted ADR is never edited on the merits — it becomes `Superseded by ADR-NNNN` and a new ADR is written.

Long, exploratory discussion still lives in `docs/superpowers/specs/`. The ADR is the short summary of the final decision.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-layered-architecture.md) | Layered architecture with ports and registries | Accepted | 2026-09-03 |
| [0002](0002-cli-json-contract.md) | The CLI as a JSON contract for external agents | Accepted | 2026-09-03 |
| [0003](0003-config-credentials-separation.md) | Separating configuration from credentials | Accepted | 2026-09-03 |
| [0004](0004-single-package.md) | A single `job_hunter_ai` package under `src/` | Accepted | 2026-09-03 |
