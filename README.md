# job-hunter-ai

[![CI](https://github.com/NavesDev/job-hunter-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/NavesDev/job-hunter-ai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230)](https://docs.astral.sh/ruff/)

🤖 A foundation for automating job applications, designed to be driven by AI agents (local or external).

The CLI scripts are **pure and AI-free**: any agent (Claude Code, another LLM, or a human) orchestrates from the outside — deciding whether to apply and with which data — and calls the scripts through flags and arguments. The mechanical work (sending an email, filling a known form) stays in deterministic code.

Docs: [Architecture](docs/ARCHITECTURE.md) · [Features](docs/FEATURES.md) · [Current sprint](docs/sprints/SPRINT-01-MVP.md) · [CLI contract](docs/CONTRACT.md) · [Data model](docs/DATA_MODEL.md) · [Code standards](docs/CODE_STANDARDS.md) · [Testing standards](docs/TESTING.md) · [ADRs](docs/adr/README.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Status

🚧 **Alpha.** The MVP works end to end: `list-jobs` normalizes a JSON file into the local database, and `apply-job` emails the application with the resume attached, recording every attempt. Still to come: platform scrapers, form applications and batch mode — see [FEATURES.md](docs/FEATURES.md).

## Requirements

Python 3.11+.

## Installation

```bash
git clone git@github.com:NavesDev/job-hunter-ai.git
cd job-hunter-ai
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp config/config.example.yaml config/local/config.yaml
cp config/templates/email-body.example.html config/local/email-body.html
cp .env.example .env
# edit config/local/config.yaml with non-sensitive settings (name, resume, preferences)
# edit .env with credentials (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, ...)
# customize config/local/email-body.html (free-form HTML, your own styling)
# drop your resume at config/local/resume.pdf (or point elsewhere in config.yaml)
```

`config/local/` and `.env` are gitignored. Non-sensitive settings (name, paths, preferences) live in `config/local/config.yaml`; credentials and secrets (SMTP, per-platform logins) live in `.env` — never in the YAML, never committed. Use a dedicated **app password**, never your account's main password (see [SECURITY.md](SECURITY.md)).

## Usage

### List jobs

```bash
list-jobs --source manual --file jobs.json --max-length 100
```

| Flag | Required | Description |
|---|---|---|
| `--source` | yes | Registered job source (`manual`, `geekhunter`) |
| `--file` | source-dependent | Path to the input JSON/CSV (`manual` source) |
| `--max-length` | no (default 50) | Maximum number of jobs returned |
| `--filter` | no | Listing filter as `name=value`, repeatable (`geekhunter` source) |

The `manual` source expects a JSON list; `title` and `company` are required, everything else optional:

```json
[
  {"title": "Backend Engineer", "company": "Acme", "url": "https://acme.com/jobs/1",
   "description": "Python, SQL", "apply_email": "jobs@acme.com"}
]
```

#### GeekHunter

```bash
list-jobs --source geekhunter --max-length 20
```

Collects from GeekHunter's public listing. It takes no flag of its own — what it
collects is set in `config/local/sources/geekhunter.yaml`, copied from
[`config/sources/geekhunter.example.yaml`](config/sources/geekhunter.example.yaml):

```yaml
filters:
  workModality: "remote"      # remote | hybrid | on-site | remote-in-city
  experienceLevel: "senior"   # intern | entry | mid | senior | manager
  searchTerm: "python"
```

For a one-off run, `--filter name=value` (repeat it) takes the place of the whole
`filters:` mapping in the YAML — the two are never merged, so a run states its filters
in full:

```bash
list-jobs --source geekhunter --filter workModality=remote --filter searchTerm=python
```

An unknown filter name or value raises `INVALID_INPUT` **before** any request goes
out: the platform silently ignores a bad filter and returns its whole listing, which
would quietly hand you the wrong jobs. So does an argument that is not a `name=value`
pair. The `manual` source takes no `--filter`.

The source needs no login and reads only public pages. It identifies itself by
user-agent and paces itself to one request per second — collecting `n` jobs costs
`ceil(n / 10)` listing requests plus one detail request per job. Jobs come back with
`apply_email: null`, because the platform exposes no address; applying goes through
its form. Every filter, setting and failure mode is in
[docs/sources/geekhunter.md](docs/sources/geekhunter.md); the design behind them is in
[the spec](docs/superpowers/specs/2026-09-05-geekhunter-source-design.md).

Output: JSON on stdout, a list of normalized jobs (`id`, `source`, `title`, `company`, `description`, `url`, `apply_email`, `raw`, `collected_at`). Every run stores and deduplicates into the local SQLite database — stable ids, no duplicates across runs ([DATA_MODEL.md](docs/DATA_MODEL.md)). Errors go to stderr as `{"error": ..., "code": ...}` with a non-zero exit code ([CONTRACT.md](docs/CONTRACT.md)).

### Apply to a job

```bash
apply-job --job-id manual:d4979b84f109 --method email --email jobs@company.com --subject "Backend role - Your Name"
apply-job --job-id manual:d4979b84f109 --method form
```

#### GeekHunter's form

```bash
pip install -e ".[form]" && playwright install chromium
apply-job --job-id geekhunter:3b6557006129 --method form
```

Fills GeekHunter's fixed form from your profile and submits it in a browser
([ADR-0005](docs/adr/0005-playwright-for-form-appliers.md) explains why a browser;
[docs/sources/geekhunter.md](docs/sources/geekhunter.md) collects the whole platform).
Three things are on you, in `config/local/sources/geekhunter.yaml`:

```yaml
accept_terms: true                               # applying accepts their Terms in your name
submit: false                                    # fill the form and stop, for a first look
browser_profile_dir: "config/local/browser-profile"   # a profile you logged in with by hand
```

**No GeekHunter password, ever.** The platform identifies a candidate by email, and its
form accepts an application without a session — so the applier asks for no credential, and
there is nowhere to put one. Left anonymous, it fills the email from
`candidate.contact_email`. Point `browser_profile_dir` at a profile **you** signed into by
hand and the application ties to your existing account instead; the applier still never sees
the password, and never logs in. The phone, LinkedIn and the expected salaries come from `candidate.extra_fields`:

```yaml
candidate:
  extra_fields:
    phone: "+55 61 90000-0000"
    linkedin: "https://www.linkedin.com/in/you"
    salary_expectation_clt: "4000"
    salary_expectation_pj: "4500"
    salary_expectation_internship: "2000"
```

GeekHunter asks for the expectation in the posting's own contract type, and says which in
the field's name — so the right number is picked for you. `--salary clt|pj|internship`
overrides that:

```bash
apply-job --job-id geekhunter:6dd70e03512a --method form --salary pj
```

`--salary` never carries an amount: it names one of the values above. Only what the profile
predefines can ever be sent. A missing field raises `INVALID_INPUT` **before** the browser
opens, because an application cannot be un-sent. `status="sent"` is only
returned when GeekHunter answers with its own confirmation — anything else is `failed`,
recorded in the history with the reason.

| Flag | Required | Description |
|---|---|---|
| `--job-id` | yes (or `--all-ready`) | Job id returned by `list-jobs` |
| `--method` | yes | `email` or `form` |
| `--email` | if `method=email` and the job carries no email | Destination address |
| `--subject` | no | Email subject; falls back to the configured default |
| `--all-ready` | not yet | Batch mode; rejected with `INVALID_INPUT` until it is delivered |

The email body (`config/local/email-body.html`, falling back to `config/templates/email-body.example.html`) and the resume PDF (`config/local/resume.pdf`) are always fixed — only the method, the address and the subject vary per call. `--method form` needs an applier registered for the job's platform; without one it returns `status=skipped` instead of blocking the rest of the flow.

### Output and errors

Every command prints structured JSON. Success goes to stdout; failures go to stderr with a non-zero exit code:

```json
{"error": "smtp connection refused", "code": "SMTP_ERROR"}
```

This lets an external agent (AI or human) parse the result without depending on stack traces. Full contract in [docs/CONTRACT.md](docs/CONTRACT.md).

### Trying it without sending a real email

[MailDev](https://github.com/maildev/maildev) is a local SMTP server with a web inbox — nothing leaves the machine:

```bash
npm install            # once; installs maildev as a dev dependency
make maildev           # SMTP on :1025, inbox at http://localhost:1080
```

Point `.env` at it and apply as usual:

```bash
SMTP_HOST=127.0.0.1
SMTP_PORT=1025
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=anything
SMTP_USE_TLS=false
```

The application shows up in the inbox with the HTML body and the attached PDF. The automated tests do not need it: they run their own in-process fake SMTP server.

## Architecture at a glance

```
cli/  →  application/  →  domain/
                              ↑
                           infra/ (implements domain/ports)
```

Every job source (`JobSource`) and every application method (`JobApplier`) is a pluggable strategy resolved through a registry — a new platform lands in `infra/` without touching `application`/`domain`. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); decisions in [docs/adr/](docs/adr/README.md).

## Development

```bash
pip install -e ".[dev]"
make check     # ruff + ruff format --check + mypy + import-linter + pytest (same gate as CI)
```

The dependency rule between layers is enforced, not just documented: `import-linter` contracts declared in `pyproject.toml` fail the build if `application/` ever imports `infra/`, or if anything leaks into `domain/`.

Tests follow the **AAA** pattern (Arrange/Act/Assert, spelled out in comments). Every new piece of code in `domain/`, `application/` or `infra/` needs a test before merge. See [docs/TESTING.md](docs/TESTING.md), [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

This is job application automation. Whoever runs it is responsible for how it is used:

- **Terms of Service.** Job platforms (LinkedIn, Gupy, Indeed and others) restrict or forbid automated collection and account automation. This project ships no scraper for any platform; every new source must be checked against the site's ToS before being implemented and used.
- **No bulk blasting.** The tool is meant for personal applications, one at a time. Do not use it for mass sending — it is bad for the people receiving it and may qualify as spam.
- **Truthful data.** The resume and profile you send must be yours and accurate.
- **Personal data.** Your resume, history and credentials stay on your machine, in gitignored files. The project sends nothing to any third-party service.
- **Human review.** Automation sends exactly what you configured; check the email body and the recipient before applying in batch.

The project is provided "as is", without warranty, under the [MIT license](LICENSE).

## Roadmap

Current and planned deliverables in [docs/FEATURES.md](docs/FEATURES.md). Sprint in progress in [docs/sprints/SPRINT-01-MVP.md](docs/sprints/SPRINT-01-MVP.md). History in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
