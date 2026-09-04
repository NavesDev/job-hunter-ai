# Sprint 01 — MVP: list jobs and apply by email

- **Status:** in progress — TASK-01 delivered, TASK-02 pending
- **Start:** 2026-09-03
- **Sprint goal:** starting from a hand-made list of jobs, I can list them through the CLI and email my application to one of them, without editing any code.

The sprint is delivered when both tasks below are closed, in order. TASK-02 depends on TASK-01 (it needs the job persisted with a stable id).

## Scope

In:

- The `manual` source (a JSON file written by you or by an agent).
- Local persistence in SQLite, deduplicated by a stable id.
- Sending an application by email (SMTP), with a fixed HTML body and the resume PDF attached.
- The JSON output contract (stdout/stderr/exit code) holding for both commands.

Out (for later):

- Any platform scraper; `--method form`; `--all-ready`; the AI layer; multiple resumes; automatic retries.

## Definition of done (applies to both tasks)

- [ ] `make check` green (ruff + ruff format + mypy + import-linter + pytest).
- [ ] A test in the AAA pattern for every new piece of code in `domain/`, `application/` and `infra/`.
- [ ] A CLI test checking the output against [CONTRACT.md](../CONTRACT.md) (fields, exit code).
- [ ] Dependency rule respected: `application/` receives ports by injection and never imports `infra/` (`make layers` proves it).
- [ ] No credential in a log, an error or the JSON output.
- [ ] [CHANGELOG.md](../../CHANGELOG.md) updated under `Unreleased`.

---

## TASK-01 — List jobs from a manual file

**Deliverable:** I run `list-jobs --source manual --file jobs.json` and get, on stdout, the normalized list of jobs, already stored in the local database and ready to be used by `apply-job`.

**Branch:** `feat/2-list-jobs-manual` — issue [#2](https://github.com/NavesDev/job-hunter-ai/issues/2)

**How to validate (as the user):**

```bash
cat > jobs.json <<'JSON'
[
  {"title": "Backend Engineer", "company": "Acme", "url": "https://acme.com/jobs/1",
   "description": "Python, SQL", "apply_email": "jobs@acme.com"}
]
JSON

list-jobs --source manual --file jobs.json --max-length 10
# stdout: JSON with one item whose id is "manual:<hash>"; exit code 0

list-jobs --source manual --file jobs.json
# run it again: same ids, no duplicates in the database
```

**Acceptance criteria:**

- [ ] Every job carries all the contract fields: `id`, `source`, `title`, `company`, `description`, `url`, `apply_email`, `raw`, `collected_at`.
- [ ] `id` is deterministic and follows the rule in [DATA_MODEL.md](../DATA_MODEL.md#job-identity) — two runs over the same input produce the same id.
- [ ] Running twice does not duplicate a row in SQLite and preserves the `collected_at` of the first collection.
- [ ] `--max-length` caps the result; the default is 50.
- [ ] An unknown `--source` exits with `SOURCE_NOT_FOUND` on stderr and a non-zero exit code.
- [ ] A missing file or invalid JSON exits with `INVALID_INPUT` on stderr and a non-zero exit code.
- [ ] The database is created on first run, at the path from `storage.database_path`.
- [ ] Stdout contains **only** the JSON — no stray logs.

**Expected work:** `ManualJsonJobSource` plus the source registry, `SqliteJobRepository` with the initial migration, `ListJobsUseCase`, `config/loader.py`, and the real `list-jobs` command replacing the `NOT_IMPLEMENTED` stub.

---

## TASK-02 — Apply to a job by email

**Deliverable:** I run `apply-job --job-id <id> --method email` and the company receives my application email, with my HTML body and my resume attached as a PDF; the outcome of the attempt is recorded in the local history.

**Depends on:** TASK-01.

**How to validate (as the user):**

```bash
cp .env.example .env                 # fill SMTP_* with an app password
cp config/config.example.yaml config/local/config.yaml
cp config/templates/email-body.example.html config/local/email-body.html
cp ~/resume.pdf config/local/resume.pdf

apply-job --job-id manual:<hash> --method email --email jobs@company.com \
          --subject "Backend role - Your Name"
# stdout: {"job_id": "...", "method": "email", "status": "sent", ...}; exit code 0
```

**Branch:** `feat/3-apply-job-email` — issue [#3](https://github.com/NavesDev/job-hunter-ai/issues/3)

**Acceptance criteria:**

- [ ] The output matches the contract's `ApplicationResult`: `job_id`, `method`, `status`, `applier`, `detail`, `applied_at`.
- [ ] The email uses the body from `config/local/email-body.html`, falling back to the versioned example template when the local file is missing.
- [ ] The resume from `application.resume_path` is attached as a PDF.
- [ ] Recipient: `--email` when passed; otherwise the job's `apply_email`; with neither, `INVALID_INPUT`.
- [ ] Subject: `--subject` when passed; otherwise the configured `default_subject`, with its placeholders resolved.
- [ ] Every attempt inserts a row in `applications`, failures included (`status="failed"` with the reason in `detail`).
- [ ] An SMTP failure exits as `SMTP_ERROR` on stderr with a non-zero exit code, **without** leaking the username or password.
- [ ] An unknown `--job-id` exits as `JOB_NOT_FOUND`.
- [ ] `--method form` returns `status="skipped"` with exit code 0 — not an error, a valid result.
- [ ] No test sends a real email: a local fake SMTP server is used.

**Expected work:** `EmailApplier` plus the applier registry, body/subject rendering, PDF attachment, `ApplyJobUseCase`, `save_application` in the repository, and the real `apply-job` command replacing the stub.

---

## Closing the sprint

When TASK-02 closes:

- Remove `NotImplementedYetError` from `domain/errors.py` and the `NOT_IMPLEMENTED` paragraph from [CONTRACT.md](../CONTRACT.md) — the code was temporary and goes away with the stubs.
- Tick the matching items in [FEATURES.md](../FEATURES.md).
- Tag `v0.1.0` and move `Unreleased` into a release section in the CHANGELOG.
