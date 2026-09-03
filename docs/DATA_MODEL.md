# Data model

The project's local state: a single SQLite database at `config/local/jobs.db` (gitignored). It holds collected jobs and application history. It never leaves the machine — see [SECURITY.md](../SECURITY.md).

## Schema

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,   -- see "Job identity"
    source        TEXT NOT NULL,      -- "manual", "linkedin", ...
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    url           TEXT,
    apply_email   TEXT,
    raw           TEXT NOT NULL DEFAULT '{}',  -- original source payload, JSON, for auditing
    collected_at  TEXT NOT NULL       -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs (source);

CREATE TABLE IF NOT EXISTS applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    method      TEXT NOT NULL,        -- "email", "form"
    status      TEXT NOT NULL,        -- "sent" | "failed" | "skipped"
    applier     TEXT NOT NULL,        -- name of the applier that ran
    detail      TEXT NOT NULL DEFAULT '',
    applied_at  TEXT NOT NULL         -- ISO 8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications (job_id);

CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);
```

Dates are always `TEXT` in ISO 8601 UTC (`2026-09-03T14:00:00Z`), matching the [CLI contract](CONTRACT.md). `raw` is serialized JSON — a native JSON type is not guaranteed in every SQLite build.

## Job identity

`Job.id` has the shape `"<source>:<hash12>"` — for example `manual:a1b2c3d4e5f6`.

- `hash12` is the first 12 characters of the SHA-256 of a natural key, normalized (`strip()` + `lower()`) and joined with `\x1f`.
- The natural key is the first available of:
  1. an `external_id` provided by the source;
  2. the job `url`;
  3. `company` + `title` (fallback for a manual source with no url).
- The `source` prefix guarantees that the same posting coming from two platforms does not silently collide.
- The id is **deterministic**: running `list-jobs` twice over the same input produces the same ids.

## Deduplication

`save_jobs` is idempotent: `INSERT ... ON CONFLICT (id) DO UPDATE` refreshes the mutable fields (`title`, `company`, `description`, `url`, `apply_email`, `raw`) and **preserves** the original `collected_at` — the date belongs to the first collection, not the latest one.

Consequence: running `list-jobs` repeatedly neither inflates the database nor loses the application history already tied to that id.

## Application idempotency

Applying has an external effect (an email goes out). The rules:

1. Every attempt inserts a **new row** in `applications` — the history is append-only, never overwritten.
2. `apply-job` does not block resending by default: if the user or agent asks again, it sends again. Deciding "I already applied here" belongs to the orchestrator, which can consult the history.
3. `--all-ready` **skips** jobs that already have an application with `status="sent"`, so a batch never spams a company.
4. A send failure records `status="failed"` with the reason in `detail` before the error propagates to the CLI. No silent failures.

## Retries

No automatic retry in phase 1. An SMTP failure becomes `SMTP_ERROR` and the orchestrator decides whether to try again — this avoids re-sending the same email several times on a partial failure (an error raised after `DATA` was already accepted).

## Schema migrations

Phase 1 uses hand-written versioned SQL, no Alembic (one table each, a disposable local database):

- `schema_version` records the applied version.
- On open, the repository applies the pending migrations from `infra/repository/migrations/NNN_*.sql` in order.
- A destructive change (dropping or renaming a column) requires a new numbered migration and a `BREAKING` entry in the [CHANGELOG](../CHANGELOG.md).

Alembic comes in when there is more than one consumer of the database, or data that cannot simply be collected again.
