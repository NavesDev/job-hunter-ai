# Why

<!-- The problem or deliverable behind this change. The diff already shows the "what". -->

Closes #

# Deliverable

<!-- What the user can do after this PR that they could not before. -->

# How to validate

```bash
make check
# manual verification command, if any
```

# Checklist

- [ ] Branch named `type/issue-id-description` (e.g. `feat/12-manual-json-source`).
- [ ] Conventional Commits with a layer scope: `feat(domain):`, `fix(infra):`, `test(application):`, `docs(cli):`.
- [ ] `make check` passes locally (ruff + mypy + pytest).
- [ ] New code in `domain/`, `application/` or `infra/` has a test in this PR, in the AAA pattern.
- [ ] Dependency rule respected (`domain/` imports nothing; `application/` receives ports by injection).
- [ ] CLI contract changes reflected in [docs/CONTRACT.md](../docs/CONTRACT.md).
- [ ] User-visible changes recorded in [CHANGELOG.md](../CHANGELOG.md) under `Unreleased`.
- [ ] No credentials, resume or personal data in the diff.
