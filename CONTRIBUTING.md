# Contributing

Everyone interacting with this project agrees to the [Code of Conduct](CODE_OF_CONDUCT.md). Security flaws do **not** go into public issues — follow [SECURITY.md](SECURITY.md).

## Before you start

Read, in this order:

1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — layers, dependency rule, strategy/registry.
2. [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) — style, SOLID, what not to do.
3. [docs/TESTING.md](docs/TESTING.md) — AAA pattern, test layout.
4. [docs/CONTRACT.md](docs/CONTRACT.md) — if the change touches the CLI (flag, output field, exit code).
5. [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — if the change touches the database, job ids or history.

## Environment

```bash
python -m venv .venv && source .venv/bin/activate
make install          # editable install + pre-commit hooks
make check            # same gate as CI: ruff + format + mypy + pytest
```

## Branch naming

```
<type>/<issue-id>-<short-description-in-kebab-case>
```

- `<type>`: same vocabulary as commits — `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- `<issue-id>`: number of the issue the branch closes. No issue yet? Open one first — traceability starts there.
- `<short-description>`: 2 to 5 words, kebab-case.

Examples: `feat/12-manual-json-source`, `fix/31-smtp-timeout`, `docs/8-layering-adr`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/), **with a mandatory layer scope**:

```
<type>(<layer>): <imperative description, lowercase, no trailing period>
```

Valid scopes, one per commit — whatever the change actually touches:

| Scope | When to use it |
|---|---|
| `domain` | entity, port, typed error |
| `application` | use case |
| `infra` | source, applier, repository, SMTP, SQLite |
| `cli` | command, flag, output formatting |
| `config` | loader, example files, `.env.example` |
| `docs` | any document under `docs/` or at the root |
| `adr` | architecture decision under `docs/adr/` |
| `ci` | workflow, pre-commit, Makefile |
| `deps` | dependency in `pyproject.toml` |

Examples:

```
feat(infra): add EmailApplier with resume attachment
fix(cli): keep stdout clean when the applier fails
test(application): cover apply-job with no registered applier
docs(adr): record the config/credentials split
```

When type and scope would repeat each other (`docs(docs)`), drop the scope: `docs: ...`.

A change that **breaks** the CLI contract carries `!` plus a footer: `feat(cli)!: ...` and `BREAKING CHANGE: <what broke>`.

A commit touching more than one layer should be split. If it is genuinely atomic (a new port plus its implementation), use the scope of the outermost layer involved.

## Pull request flow

1. Branch off `main`, following the naming rule above.
2. TDD where it makes sense: test first (AAA), then the code.
3. `make check` green locally before opening the PR — CI runs the same gate on Python 3.11 and 3.12.
4. PR against `main`, filling in the [template](.github/PULL_REQUEST_TEMPLATE.md). The description explains *why*; the diff already shows *what*.
5. Any change in `domain/`, `application/` or `infra/` needs a test in the same PR.
6. Any change to the [CLI contract](docs/CONTRACT.md) (flag, JSON field, exit code, error code) updates `CONTRACT.md` in the same PR — never afterwards.
7. Any change to the database or to the id/dedup rules updates [DATA_MODEL.md](docs/DATA_MODEL.md) and adds the numbered migration.

## New platform (source or applier)

No need to touch `application/` or `domain/` — only:

1. A new class in `src/job_hunter_ai/infra/sources/<platform>.py` (implementing `JobSource`) or `src/job_hunter_ai/infra/appliers/<platform>_form_applier.py` (implementing `JobApplier`).
2. Registration in the matching registry.
3. A unit test (with a fake) plus an integration test if real network or a real form is involved.
4. If it needs its own settings: `config/local/sources/<platform>.yaml` (non-sensitive) plus prefixed variables in `.env.example` (credentials).
5. Confirm the platform's Terms of Service before opening the PR — see [Responsible use](README.md#responsible-use).

## Changelog

Every user-visible change (new deliverable, new flag, contract change, relevant bugfix) goes into [CHANGELOG.md](CHANGELOG.md) under `Unreleased`, in the same PR.

## Design questions

Small change: discuss it in the PR. Architectural change (new layer, new port, breaking contract): open an [ADR](docs/adr/README.md) before implementing. Long exploration before the decision can live as a spec in `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`; the ADR is the short summary of what was decided.
