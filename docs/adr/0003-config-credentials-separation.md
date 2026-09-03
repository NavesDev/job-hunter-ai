# ADR-0003: Separating configuration from credentials

- **Status:** Accepted
- **Date:** 2026-09-03
- **Deciders:** NavesDev

## Context

The project handles sensitive data (SMTP password, future platform logins) alongside data that is personal but not secret (name, resume path, default subject). Mixing both in one file increases the odds of committing a secret.

## Decision

Two distinct places: non-sensitive configuration in `config/local/config.yaml` (with a versioned example at `config/config.example.yaml`); credentials in `.env` at the root, loaded by `python-dotenv` (with a versioned example at `.env.example`). Platform credentials use a per-source prefix (`LINKEDIN_USERNAME`). Both real files are gitignored.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Everything in one `config.yaml` | A single mistaken `git add` leaks the password along with the preferences |
| Environment variables only | Structured settings (lists, extra fields) become awkward as env vars |
| The operating system keyring | Platform-dependent; gets in the way of headless/CI use |

## Consequences

**Positive:** the leak surface shrinks to a single file, whose name is known to both `.gitignore` and the `detect-private-key` hook. Configuration can be inspected and reviewed without exposing a secret.

**Negative / accepted cost:** `config/loader.py` has to read two sources and merge them; the user copies two example files during setup.
