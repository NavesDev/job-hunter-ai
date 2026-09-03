# ADR-0002: The CLI as a JSON contract for external agents

- **Status:** Accepted
- **Date:** 2026-09-03
- **Deciders:** NavesDev

## Context

Whoever orchestrates the flow (an AI agent or a human) needs to consume the scripts' results programmatically, without parsing free text or stack traces, and without answering an interactive prompt.

## Decision

Every command is non-interactive and prints JSON: success on stdout, a structured error (`{"error", "code"}`) on stderr with a non-zero exit code. The full contract lives in [docs/CONTRACT.md](../CONTRACT.md) and is verified by tests in `tests/cli/`.

## Alternatives considered

| Alternative | Why not |
|---|---|
| An importable Python library instead of a CLI | Ties the orchestrator to Python and to the agent's own process |
| Human-readable text output | Forces the agent into fragile parsing |
| Errors signaled by exit code only | Loses the reason for the failure; the agent cannot tell whether to try another method |
| An HTTP/MCP server | Too much infrastructure and lifecycle for local single-user use |

## Consequences

**Positive:** any agent, in any language, can consume the scripts. `status="skipped"` is a valid result (exit 0), not an error — the agent keeps processing the batch.

**Negative / accepted cost:** no debug `print()` may go to stdout; diagnostic logs must go to stderr. Changing a field requires versioning the contract.
