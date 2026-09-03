# Security Policy

This project handles **credentials** (SMTP password or app password, future platform logins) and **personal data** (resume PDF, name, email, phone). Treat the local repository as sensitive material.

## Supported versions

Pre-release (`0.x`). Only `main` receives security fixes until the first stable release.

## Reporting a vulnerability

Do not open a public issue for a vulnerability. Use [GitHub Security Advisories](https://github.com/NavesDev/job-hunter-ai/security/advisories/new) (*Security* tab → *Report a vulnerability*).

Include: description, impact, reproduction steps, and the version or commit. Expect a response within 7 days.

## Threat model (summary)

| Asset | Where it lives | Main risk | Mitigation |
|---|---|---|---|
| SMTP password | `.env` | Leaking through a commit or a log line | `.env` gitignored, `detect-private-key` hook, never log credentials |
| Resume PDF (PII) | `config/local/resume.pdf` | Accidental commit | `config/local/` gitignored |
| Application history | `config/local/jobs.db` (SQLite) | PII exposure if the file is shared | Stays local, gitignored, never leaves the machine |
| Platform credentials (phase 2) | `.env`, prefixed per source | Wrong applier reusing them | Mandatory per-source prefix (`LINKEDIN_*`) |

## Security rules for the code

1. Credentials only come from `.env` (via `python-dotenv`). Never from YAML, never from a CLI flag, never hardcoded.
2. No credential, email body or resume content may appear in a log, an error message or the JSON output — stderr included.
3. SMTP failures are reported as `{"error": "...", "code": "SMTP_ERROR"}` with no echo of the username or password.
4. No credentials in tests. Tests use a local fake SMTP server; no test touches an external network.
5. Use a dedicated **app password** (Gmail/Outlook), never the account's main password. Revoke it if you suspect a leak.
6. The SQLite database and `.env` are not encrypted — protect them at the filesystem level.

## Responsible use

See the *Responsible use* section of the [README](README.md#responsible-use). Application automation may violate the Terms of Service of job platforms; responsibility for use lies with whoever runs it.
