-- Initial schema. Mirrors docs/DATA_MODEL.md.
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    url           TEXT,
    apply_email   TEXT,
    raw           TEXT NOT NULL DEFAULT '{}',
    collected_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs (source);

CREATE TABLE IF NOT EXISTS applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    method      TEXT NOT NULL,
    status      TEXT NOT NULL,
    applier     TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    applied_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications (job_id);
