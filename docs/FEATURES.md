# Features and planning

Every item is a **deliverable**: something the user gains the ability to do. Classes, ports and modules are implementation detail — they live in [ARCHITECTURE.md](ARCHITECTURE.md), not here.

## Sprint 01 — MVP (done)

Detail, acceptance criteria and ordering in [docs/sprints/SPRINT-01-MVP.md](sprints/SPRINT-01-MVP.md).

- [x] **List jobs from a hand-made list** — I point at a JSON file and get normalized jobs back as JSON, stored locally with stable ids and no duplicates across runs.
- [x] **Apply to a job by email** — I pick a listed job and send my application with my own HTML body and my resume attached as a PDF; the outcome lands in the local history.

## Foundation (done)

- [x] **Install and run the project** — `pip install -e .` exposes `list-jobs` and `apply-job`; example configuration is versioned.
- [x] **A stable contract for agents** — JSON output, structured errors and exit codes documented in [CONTRACT.md](CONTRACT.md) and verified by tests.
- [x] **Secrets separated from configuration** — credentials only in `.env`, settings in the local YAML, both kept out of version control.
- [x] **Automated quality gate** — `make check` and CI run lint, formatting, types and tests on every PR.

## Next deliverables (prioritized backlog)

Each one plugs into the existing structure and blocks none of the others.

### Short term

- [ ] **Import jobs from CSV** — I paste a platform's export without converting it to JSON first.
- [ ] **See what I already applied to** — I query the local application history per job, with status and date.
- [ ] **Apply in batch** — `--all-ready` fires applications for every ready job, skipping the ones already sent.
- [ ] **Choose between several resumes** — I select a profile (backend, frontend...) when applying; today the resume is single and fixed.

### Medium term

- [ ] **Collect jobs straight from a platform** — one source per site (LinkedIn, Gupy, Indeed) brings jobs in without a manual export. Before implementing any of them: check the platform's Terms of Service (see [Responsible use](../README.md#responsible-use)).
- [ ] **Apply on sites that only accept a form** — automatic filling of the platform's form with the profile data, for sites with no contact address.
- [ ] **Resume from a failure without resending** — controlled send retries that cannot deliver the same application twice.

### Under evaluation

- [ ] **Extract the address and subject from the job description** — today the external agent does this and passes the result as flags. It only becomes a command (`enrich-job`) if owning the extraction is worth the maintenance cost.
- [ ] **Decide automatically whether to apply** — job × resume comparison with a score and a rationale (`decide-job`). Same evaluation: for now it belongs to the external orchestrator.

## Assumed limits

- Local, single-user use. No server, no multi-account, no queue.
- The "apply or not" decision belongs to the orchestrating agent, not to this project.
- No minimum test coverage gate in CI yet — the number gets defined once there is enough code to measure.
