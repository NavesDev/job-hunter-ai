# ADR-0005: Playwright for form appliers, and only for them

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** NavesDev

## Context

[Issue #6](https://github.com/NavesDev/job-hunter-ai/issues/6) brings GeekHunter in as the
first real platform. The [phase 1 investigation](../superpowers/specs/2026-09-05-geekhunter-source-design.md)
found the two halves of that platform to be nothing alike:

- **Collecting** is plain HTML. The listing and the job pages are server-rendered, anonymous,
  and each job carries a `JobPosting` JSON-LD block. A paced `urllib` GET is enough, and that
  is what shipped — no browser, no dependency.
- **Applying** is not. The form has no `action`, no `method` and no hidden input: it submits
  through a **Next.js Server Action** — a `POST` to the page's own URL with a `Next-Action`
  header whose id is generated per build, a React-flight-encoded multipart body carrying the
  PDF, a Cloudflare edge in front, and a session that lives in an `auth_token` cookie next to
  an `XSRF-TOKEN`. Some postings then add a screening-question step.

So the question is not "browser or not" for the project. It is "browser or not for the applier".

## Decision

Drive form appliers with **Playwright**, added as the optional `form` extra
(`pip install -e ".[form]"`). Sources stay on plain HTTP. No other layer may import it.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Raw HTTP against the Server Action | The action id has to be scraped out of a minified JS chunk and the flight payload re-encoded by hand. It breaks on every GeekHunter deploy, and the failure mode of a wrong guess is a broken — or duplicated — application to a real company. |
| The site's GraphQL API (`POST /graphql`) | It exists and serves the candidate dashboard, but its bundles carry no application mutation. The apply flow lives entirely in the Server Action. Using GraphQL would mean guessing at an undocumented, unused-by-the-site mutation. |
| Selenium | Same cost, worse ergonomics: heavier setup, no first-class `expect`/auto-waiting, and no bundled browser download. |
| Requests plus a hand-rolled session | Does not address the Server Action at all — the transport is the problem, not the cookies. |
| Do not automate applying at all | The fixed form is exactly the mechanical work this project exists to remove. Giving it up removes the deliverable. |

## Consequences

**Positive:**

- The applier drives the page the way the candidate does, so it keeps working across GeekHunter
  deploys: what breaks it is a *visible* change to the form, which the field-name assertions
  catch loudly instead of silently mis-submitting.
- The confirmation the platform renders ("Candidatura Completa!") becomes the evidence behind
  `status="sent"` — a real assertion, not an assumed 200.
- A screening-question step is observable, so the applier can report it instead of pretending
  the application is finished.

**Negative / accepted cost:**

- A ~400 MB browser download, kept out of the default install: `job-hunter-ai` still installs
  with three runtime dependencies, and CI never installs a browser for the unit suite.
- Applying is slower — seconds, not milliseconds. Irrelevant for one application at a human pace.
- A second execution model to reason about (a live page, timeouts, waits) confined to
  `infra/appliers/`. `import-linter` keeps `playwright` out of `domain/`.
- The applier consumes a browser profile the user already logged into. It never logs in, never
  handles a password, and fails fast when the session is gone.
