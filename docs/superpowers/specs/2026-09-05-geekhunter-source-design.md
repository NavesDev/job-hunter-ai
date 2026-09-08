# GeekHunter — source and form applier design (issue #6, phase 1)

Date: 2026-09-05
Status: Proposed
Issue: [#6](https://github.com/NavesDev/job-hunter-ai/issues/6)

Investigation of [GeekHunter](https://www.geekhunter.com) as the first real platform, answering
the phase 1 questions of issue #6. All findings come from a read-only session against the live
site on 2026-09-05: public pages fetched anonymously, plus the authenticated candidate area of
the repository owner's own account. **No application was submitted and no form was posted.**

## Summary of the decision

| Deliverable | Transport | Why |
|---|---|---|
| `GeekHunterJobSource` | plain HTTP (`httpx`) + HTML parsing | pages are fully server-rendered, anonymous, and carry a `JobPosting` JSON-LD block per job |
| `GeekHunterFormApplier` | Playwright (**new dependency, needs an ADR**) | the apply form submits through a Next.js **Server Action**, not a documented endpoint |

Detail and evidence below.

---

## Access and terms

**Terms of Service — not assessed.** The repository owner explicitly directed that the legal
gate be skipped for this investigation. This spec therefore records a **premise, not a
verification**: the owner asserts that automating their own candidate account on GeekHunter is
acceptable. [README §Responsible use](../../../README.md#responsible-use) still applies to
whoever runs the tool, and the owner owns that call.

**robots.txt** (`https://www.geekhunter.com/robots.txt`) — relevant excerpt, `User-agent: *`:

```
Content-Signal: search=yes, ai-input=yes, ai-train=no
Allow:    /pt/candidates/signup
Disallow: /pt/candidates
Disallow: /pt/companies
Disallow: /pt/vagas-
Disallow: /pt/jobs
Disallow: /pt/entrar
```

Consequences for the paths we need:

- `/pt/vagas` (listing) — **not disallowed**. Only the `/pt/vagas-` prefix is.
- `/pt/<company-slug>/jobs/<job-slug>` (job detail) — **not disallowed**. `Disallow: /pt/jobs`
  is a prefix rule and does not match a path that starts with the company slug.
- `/pt/candidates/*` (candidate dashboard) — **disallowed**. The applier does not crawl it; it
  acts inside an interactive session as the logged-in user, which is not crawling. Worth being
  explicit about in the PR anyway.

**Authentication.** Cookie-based. After login the browser holds `auth_token` (opaque bearer,
consumed by the site's GraphQL backend), `user_type`, and `XSRF-TOKEN`. Session lifetime was
not measured; the session observed was several days old and still valid. There is no documented
token-refresh endpoint, and re-login is a form on a `Disallow`ed path — so **the applier assumes
a browser profile that is already logged in** and must fail fast when it is not, rather than
trying to log in itself.

**Rate limiting.** No `429` and no rate-limit headers observed across ~25 requests. The site is
behind **Cloudflare** (`server: cloudflare`, `cdn-cgi/*` assets), so bot management is a real
possibility for non-browser clients even though it did not trigger here — see
[Risks](#risks-and-open-questions). Proposed pace: **1 request/second, sequential, no
concurrency**, which for the default `--max-length 50` is roughly one minute.

---

## Endpoints and data

### The listing is server-rendered HTML, not a JSON API

`https://www.geekhunter.com/pt/vagas` is a Next.js App Router page. Loading it fires **no**
XHR/fetch for job data — the jobs are already in the HTML and in the RSC flight payload. An
anonymous `GET` (no cookies) returns `200` with the full listing.

The React Server Component data endpoints (`/pt/vagas?...&_rsc=<hash>`) answered **`503`** even
from inside the browser, so they are not a usable alternative — one more reason to parse the
rendered HTML.

The candidate dashboard (`/v1/pt/candidates/dashboard`) is a separate, older Next.js app that
talks to `POST /graphql` with named operations (`GetCandidateProfileData`, `UpdateCandidate`,
`SearchCandidates`, ...). **No job-application mutation appears in its bundles** — the apply flow
belongs entirely to the new app. We do not use GraphQL.

### Pagination and filters

Both are plain query parameters on `/pt/vagas`, verified by fetching each and reading the
`N vagas disponíveis` counter (`822` unfiltered at the time of the investigation):

| Parameter | Example | Verified effect |
|---|---|---|
| `page` | `?page=2` | 10 jobs per page, 83 pages |
| `searchTerm` | `?searchTerm=python` | 822 → 159 |
| `workModality` | `?workModality=remote` | 822 → 339 |
| `workModality` | `?workModality=hybrid` | 822 → 206 |
| `experienceLevel` | `?experienceLevel=senior` | 822 → 384 (lowercase; `SENIOR` is ignored) |
| `publishedAfter` | `?publishedAfter=2026-08-30T01:26:50.496Z` | ISO 8601 instant |
| `cityName` | `?cityName=São Paulo das Missões - RS` | free text in the `City - UF` shape |

Unknown values silently return the unfiltered set (`workModality=in_person` gave 822) — the
platform does **not** fail on a bad filter. That is a fail-fast hazard: the source must validate
filter values against a known set before requesting, or it will quietly hand back the wrong
jobs.

The salary-range parameter was not identified.

### Per-job data

Each job detail page carries a `JobPosting` JSON-LD block — the whole payload, structured, no
scraping of visual markup required:

```json
{
  "@type": "JobPosting",
  "identifier": {"@type": "PropertyValue", "name": "GeekHunter", "value": "<64-char opaque id>"},
  "url": "https://www.geekhunter.com/pt/ntt-data/jobs/desenvolvedor-backend--python-e-pyspark--1",
  "title": "Desenvolvedor Backend (Python e PySpark)",
  "hiringOrganization": {"@type": "Organization", "name": "NTT DATA", "logo": "...", "sameAs": "..."},
  "description": "<p><strong>Requisitos</strong></p>... (HTML)",
  "datePosted": "2026-09-04",
  "validThrough": "2026-12-03T17:41:27.578Z",
  "employmentType": ["FULL_TIME"],
  "jobLocationType": "TELECOMMUTE",
  "applicantLocationRequirements": [{"@type": "Country", "name": "BRA"}],
  "experienceRequirements": {"monthsOfExperience": 48},
  "skills": "Pandas, Python, Numpy, Docker, ...",
  "directApply": true
}
```

The listing page carries only an `ItemList` of the 10 detail URLs — no per-job fields. So
collecting `N` jobs costs `ceil(N/10)` listing requests **plus** `N` detail requests.

Mapping onto our [`Job`](../../../src/job_hunter_ai/domain/entities/job.py):

| `Job` field | Source | Note |
|---|---|---|
| `title` | `JobPosting.title` | |
| `company` | `JobPosting.hiringOrganization.name` | the URL slug is a fallback |
| `description` | `JobPosting.description` | **HTML**, not plain text — see below |
| `url` | `JobPosting.url` | canonical, absolute |
| `apply_email` | — | GeekHunter never exposes an address; always `None` |
| `raw` | the whole JSON-LD object | keeps everything with no home |

Fields with no home yet, all preserved in `raw`: `datePosted`, `validThrough`, `employmentType`,
`jobLocationType`, `applicantLocationRequirements`, `experienceRequirements.monthsOfExperience`,
`skills`, `directApply`, `hiringOrganization.logo` / `.sameAs`. Nothing here justifies a new
`Job` field in phase 2 — `raw` is exactly what [CONTRACT.md](../../CONTRACT.md) put there for.

`description` arrives as an HTML fragment. Two options, to settle in the phase 2 PR: store the
HTML verbatim (honest to the source, and the orchestrating agent reads HTML fine), or convert to
text. **Recommendation: store verbatim** — converting is a lossy transformation and this project
does not guess.

### Stable external id — yes

`JobPosting.identifier.value` is a 64-character opaque string. Verified:

- **stable**: two fetches of the same job returned the identical value;
- **unique**: two different jobs returned different values.

It becomes the `external_id` of the [job id rule](../../DATA_MODEL.md#job-identity), which is
preferred over the URL fallback. Ids stay deterministic across runs
(`build_job_id("geekhunter", external_id=...)`). No change to `DATA_MODEL.md` is needed — the
rule already ranks `external_id` first; only the note that GeekHunter supplies one.

---

## The application form

The form sits on the job detail page and is identical for every posting — the premise of the
issue holds. Read from the DOM of a real job page (never submitted):

| Label | `name` | Type | Required | Value comes from |
|---|---|---|---|---|
| Nome completo | `name` | text | yes | `CandidateProfile.name` |
| Email | `email` | text, **disabled** | yes | the logged-in account; not ours to set |
| Celular com DDD | `phone` | tel (+ country selector) | yes | `extra_fields["phone"]` |
| LinkedIn | `linkedin` | text (URL) | yes | `extra_fields["linkedin"]` |
| Currículo (CV) | `resume` | file, `accept=".pdf"` | yes | `CandidateProfile.resume_path`; defaults to the profile's stored CV |
| Remuneração mensal esperada como CLT? | `salaryExpectation.CLT` | text (BRL mask) | yes | **not collected today** |
| Li e aceito a Política de Privacidade e os Termos de Uso | *(unnamed)* | checkbox | yes | the user, per run |
| Candidatar para a vaga | — | submit | — | — |

Notes that matter for the implementation:

- The salary field name is **contract-type dependent** (`salaryExpectation.CLT` on a CLT
  posting). A PJ posting will carry a different suffix; the applier must read the field name
  from the page, not hardcode `CLT`.
- **Expected salary has no home in `CandidateProfile`.** Two ways out: a new `--salary` flag on
  `apply-job` (a CLI contract change, so `CONTRACT.md` in the same PR), or an
  `extra_fields["salary_expectation"]`. **Recommendation: `extra_fields`** — it is what the
  entity documents itself for, and it needs no contract change.
- The consent checkbox is a legal act. It must be an explicit configuration the user turns on
  (`config/local/sources/geekhunter.yaml`), never a default the code ticks on their behalf.
- `email` is disabled: the identity is the session's, which is another reason the applier needs
  a logged-in profile.
- The resume defaults to the CV already on the profile. Uploading `resume_path` on every apply
  is the honest behavior — it keeps `apply-job` deterministic instead of depending on the
  account's stored state.
- A file-size limit exists (the UI has a `{maxSize} MB` error message); the number was not read.

### Submitting needs a real browser

The form has **no `action`, no `method`, and no hidden inputs** — it is a React form whose
submit is JS-driven. The page bundles contain `createServerReference`, `callServer` and
`Next-Action`, and contain **no API base URL at all**. That is the Next.js **Server Action**
signature: the submit is a `POST` to the page's own URL carrying a `Next-Action: <action-id>`
header and a React-flight-encoded multipart body with the PDF.

The action id is generated per build (assets already carry a `?dpl=<deploy-hash>` query), so a
raw-HTTP implementation would have to scrape a minified action id out of a JS chunk and
re-encode a flight payload — and would break on **every GeekHunter deploy**. Add the Cloudflare
edge, the `auth_token` + `XSRF-TOKEN` cookie pair, and the RSC endpoints already answering
`503`, and raw HTTP is not a serious option for applying.

Verifying the exact request would have required clicking submit with an interceptor in place —
a real, irreversible application to a real company. **Not done.** The evidence above is
structural and, in my judgment, sufficient.

### There is an assertable confirmation

The page's i18n bundle carries the post-apply strings:

- `visibilityApplyConfirmationTitle` → `"Candidatura Completa!"`
- `visibilityApplyConfirmationDescription` → `"Parabéns! Você concluiu sua candidatura para a vaga "`

Waiting for that confirmation is what lets `status="sent"` mean something. Anything else — a
timeout, a validation message, a redirect — is `status="failed"` with the reason in `detail`.

### Screening questions: a second step on some jobs

The bundle also carries a whole screening-question flow (`screeningQuestionFinishApplication` →
`"Finalizar candidatura"`, `screeningQuestionRequiredError`, `screeningQuestionSuccessTitle` →
`"Respostas enviadas!"`), plus a `/candidates/screening-questions` route. Some postings ask
free-form questions **after** the fixed form, and those answers are exactly the unstructured
work this project keeps out of the scripts.

Proposed behavior, to confirm on a real posting in phase 2: the fixed form is submitted, the
screening step is **not** answered, and the result is `status="sent"` with
`detail="screening questions pending"`. Answering them is the orchestrating agent's job. If it
turns out the application does not count until the questions are answered, this becomes
`status="failed"` instead — that check is a phase 2 acceptance criterion, not a guess to ship.

---

## The decision: HTTP for the source, Playwright for the applier

**Source → plain HTTP.** Anonymous `GET` works, the data is fully server-rendered, every job
carries structured JSON-LD, pagination and filters are query parameters, and the ids are stable.
A browser would buy nothing and cost startup time, a dependency, and CI weight. `httpx` plus an
HTML parser, with the JSON-LD block as the payload. Testable against saved fixtures, no network
in CI.

**Applier → Playwright.** The submit is a build-scoped Server Action behind Cloudflare with a
session cookie, a CSRF cookie, a file upload, and a conditional second step. Reimplementing it
over raw HTTP is guesswork that breaks on each GeekHunter deploy, and the failure mode of a bad
guess is a broken or duplicated application to a real company.

Playwright is a **new dependency and needs an ADR** ([ADR-0005](../../adr/README.md)) covering:
what it is for and what it is explicitly not for (the source stays HTTP); how the browser
profile carrying the logged-in session is configured and kept out of git; how CI avoids ever
installing browsers for the unit suite; and why the dependency is confined to
`infra/appliers/`.

Splitting issue #6 into **two PRs** is the right call: the source ships and is useful on its
own, with no new dependency, while the applier carries the ADR and the browser.

## Risks and open questions

1. **Cloudflare bot management vs a Python client.** Every anonymous fetch in this investigation
   still came from a real browser. A plain `httpx` request with a library user-agent may be
   challenged. First task of the source PR: one manual `httpx` request against `/pt/vagas` from
   the dev machine. If it is challenged, the source falls back to Playwright too and the ADR
   grows.
2. **The unknown salary-range filter parameter**, and the `workModality` value for on-site.
3. **Screening questions**: whether an application counts as complete before they are answered.
4. **Already-applied state**: what the job page renders for a posting the account already
   applied to was not observed (no applied posting available). It is the natural guard against
   a duplicate application and must be identified in the applier PR.
5. **Session expiry**: lifetime unmeasured, and there is no non-browser refresh. The applier
   must detect a logged-out session and raise `INVALID_INPUT` before touching the form.
6. **No HTML structure is load-bearing except the JSON-LD block and the form field names** —
   which is the point of choosing them. Both still change without notice; the source must raise
   on a missing JSON-LD block rather than return an empty list.

## What phase 2 must not do

- No login automation: the applier consumes an existing session, it does not create one.
- No batch: `--all-ready` stays out of scope (issue #6, "Out of scope").
- No test hits GeekHunter; integration tests run on saved fixtures.
- No credential in a log, a `detail`, or an error message.
