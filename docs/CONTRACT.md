# CLI contract

The input/output contract every script (`list-jobs`, `apply-job`, and any new command) must honor. It is what lets an external agent (AI or human) consume the scripts without knowing anything about their internals.

## General rules

1. **Stdout** carries success JSON only. No logs, no debug prints, no loose text — consumers expect `json.loads(stdout)` to work directly.
2. **Stderr** carries the structured error (format below) plus logs and diagnostics.
3. **Exit code** `0` means success. Anything `!= 0` means failure; the reason is in the error JSON on stderr.
4. Every date/time field is ISO 8601 UTC (`2026-09-03T14:00:00Z`).
5. No command reads stdin interactively — everything comes from flags, arguments, or a file pointed at by a flag. The scripts must run non-interactively (an external agent cannot answer a prompt).

## `list-jobs`

**Input** (flags):

| Flag | Type | Required | Description |
|---|---|---|---|
| `--source` | string | yes | Name of a registered source (`manual`) |
| `--file` | path | source-dependent | Input file (`manual` source) |
| `--max-length` | int | no (default 50) | Maximum number of jobs returned; must be `>= 1` |

**Output** (stdout), a list of `Job`. Every field is always present; `url` and `apply_email` may be `null`. `raw` carries the untouched source payload, for auditing.

```json
[
  {
    "id": "manual:a1b2c3",
    "source": "manual",
    "title": "Backend Engineer",
    "company": "Acme",
    "description": "...",
    "url": "https://...",
    "apply_email": "jobs@acme.com",
    "raw": {},
    "collected_at": "2026-09-03T14:00:00Z"
  }
]
```

## `apply-job`

**Input** (flags):

| Flag | Type | Required | Description |
|---|---|---|---|
| `--job-id` | string | yes (or `--all-ready`) | Id returned by `list-jobs` |
| `--method` | `email` \| `form` | yes | Application method |
| `--email` | string | if `method=email` and the job carries no address | Recipient |
| `--subject` | string | no | Subject; defaults to the local configuration |
| `--all-ready` | flag | no | Applies in batch |

**Output** (stdout), an `ApplicationResult`:

```json
{
  "job_id": "manual:a1b2c3",
  "method": "email",
  "status": "sent",
  "applier": "email",
  "detail": "",
  "applied_at": "2026-09-03T14:05:00Z"
}
```

`status` is always one of `sent` / `failed` / `skipped`. `skipped` never produces a failing exit code — it is a valid result (for example, no form applier exists for that platform).

## Errors (any command)

A single JSON object on stderr:

```json
{"error": "smtp connection refused", "code": "SMTP_ERROR"}
```

Codes used in phase 1: `SOURCE_NOT_FOUND`, `APPLIER_NOT_FOUND`, `JOB_NOT_FOUND`, `SMTP_ERROR`, `INVALID_INPUT`. A new code must be documented here before being used.

`NOT_IMPLEMENTED` is **temporary**: while a command exists but has not been delivered, it answers with that code. It leaves the code and this section when [Sprint 01](sprints/SPRINT-01-MVP.md) closes.

## Compatibility

A change that **breaks** the contract (removing a field, changing a type, renaming something) requires a new major version of the package and a `BREAKING` entry in the [CHANGELOG](../CHANGELOG.md). Adding a new field to a response is always compatible (consumers must ignore unknown fields).
