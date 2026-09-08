# GeekHunter

The `geekhunter` platform in one page: what it collects, what it applies to, and every
knob that changes either. The *why* behind the design is in
[the spec](../superpowers/specs/2026-09-05-geekhunter-source-design.md); the CLI contract
this page instantiates is in [CONTRACT.md](../CONTRACT.md).

| Piece | Where |
|---|---|
| Source (`list-jobs --source geekhunter`) | `src/job_hunter_ai/infra/sources/geekhunter/` |
| Applier (`apply-job --method form`) | `src/job_hunter_ai/infra/appliers/geekhunter_form.py` |
| Settings | `config/local/sources/geekhunter.yaml` (from [the example](../../config/sources/geekhunter.example.yaml)) |
| Recorded pages | [`tests/fixtures/geekhunter/`](../../tests/fixtures/geekhunter/README.md) |

## Collecting

```bash
list-jobs --source geekhunter --max-length 20
```

The source reads only public pages, needs no login and no browser. It parses the
`application/ld+json` blocks the platform renders server-side — an `ItemList` on the
listing, a `JobPosting` on each job page — so a CSS class rename does not break it.

Cost of a run: collecting `n` jobs is `ceil(n / 10)` listing requests plus one detail
request per job. The client identifies itself by user-agent (the platform's CDN answers
`403` to the standard library's default) and paces itself to one request per second.

Jobs come back with `apply_email: null`: the platform exposes no address, so applying
goes through its form. Everything else follows the normal contract — JSON on stdout,
stored and deduplicated by a stable id ([DATA_MODEL.md](../DATA_MODEL.md)).

## Filters

The listing is filtered in two places, and they never merge.

**In the YAML**, for every run:

```yaml
filters:
  workModality: "remote"
  experienceLevel: "senior"
  searchTerm: "python"
```

**On the command line**, for one run — `--filter name=value`, repeatable, *replacing* the
whole `filters:` mapping above, so a run always states its filters in full:

```bash
list-jobs --source geekhunter --filter workModality=remote --filter searchTerm=python
```

| Filter | Values |
|---|---|
| `workModality` | `remote`, `hybrid`, `on-site`, `remote-in-city` |
| `experienceLevel` | `intern`, `entry`, `mid`, `senior`, `manager` |
| `searchTerm` | free text, matched against title and description |
| `cityName` | free text, in the platform's own `City - UF` shape |
| `minSalary`, `maxSalary` | whole numbers, monthly, BRL |
| `publishedAfter` | ISO 8601 instant |

An unknown name, an unknown value, or an argument that is not a `name=value` pair raises
`INVALID_INPUT` **before any request goes out**. This is not pedantry: GeekHunter answers
a bad filter with its *whole unfiltered listing* instead of an error
(`workModality=in_person` returned all 822 jobs during the investigation), so a source that
passed it through would quietly hand back the wrong jobs. The values above are the ones
verified against the live site.

The `manual` source takes no `--filter` and raises `INVALID_INPUT` when it gets one.

## Applying

```bash
pip install -e ".[form]" && playwright install chromium
apply-job --job-id geekhunter:3b6557006129 --method form
```

The applier drives the platform's fixed form in a browser
([ADR-0005](../adr/0005-playwright-for-form-appliers.md) explains why a browser). Three
settings are yours to make, in the same YAML:

```yaml
accept_terms: true                                    # applying accepts their Terms in your name
submit: false                                         # fill the form and stop, for a first look
browser_profile_dir: "config/local/browser-profile"   # a profile you logged into by hand
```

`submit: false` fills everything and stops: `status="skipped"`, the filled values in
`detail`, nothing sent. `status="sent"` is returned only when GeekHunter answers with its
own confirmation; anything else is `failed`, recorded in the history with the reason.

### Screening questions

Some jobs do not end at that form: GeekHunter answers the submission with questions of its
own (`Você está quase terminando`), and the candidacy stays unfinished until they are
answered. `list-jobs` records them in the job's `raw`, so they are known before a browser
opens:

```bash
list-jobs --source geekhunter --max-length 5 --filter searchTerm=rails
# raw.screeningQuestions: [{"id": 142139, "name": "Quantos anos de experiência em/com Ruby
#   on Rails você tem?", "answerType": "number", "mandatory": true, "minAnswer": 1}]

apply-job --job-id geekhunter:eb228a61b659 --method form --answer 142139=2
```

One `--answer question-id=value` per question, repeatable. Every value is checked against
the question it belongs to — type, range, offered options — and a mandatory question left
out raises `INVALID_INPUT` **before** the browser opens: discovering it on the screen with
the form already submitted would leave the candidacy half-made. Both steps happen in one
run, so the form is submitted once.

The screening screen carries a consent of its own, separate from the form's Terms box: it
declares that the candidate's data, sensitive included, may be processed for recruitment
and diversity purposes. The same `accept_terms: true` covers it — without that setting
nothing is submitted at all — and it is named here so that what gets accepted is never a
surprise.

Applying without the answers submits nothing: the run reports `APPLIER_ERROR` naming every
question asked. The applier answers none of them on its own — these are claims about the
candidate's experience, and inventing one would make it in their name.

When no confirmation and no screening screen arrive, the attempt is genuinely ambiguous — the form may have
been refused, or accepted and answered differently — so `APPLIER_ERROR` quotes the text the
page ended on, names the URL it ended at, and keeps the page itself under `diagnostics_dir`
(`config/local/diagnostics` by default). The candidate's own values are taken out of the
quoted text. Nothing is ever re-submitted automatically: a second run is a second
application, and that call is yours.

**No GeekHunter password, ever.** The platform identifies a candidate by email and its form
accepts an anonymous application, so the applier asks for no credential and there is nowhere
to put one. Left anonymous, it fills the address from `candidate.contact_email`. Point
`browser_profile_dir` at a profile **you** signed into by hand and the application ties to
your existing account instead — the applier never logs in and never sees the password.

The phone, the LinkedIn URL and the salary expectations come from `candidate.extra_fields`:

```yaml
candidate:
  extra_fields:
    phone: "+55 61 90000-0000"
    linkedin: "https://www.linkedin.com/in/you"
    salary_expectation_clt: "4000"
    salary_expectation_pj: "4500"
    salary_expectation_internship: "2000"
```

GeekHunter asks for the expectation in the posting's own contract type and says which in
the field's name, so the right number is picked for you. A job open to more than one
contract asks once per type, and every field is required — each is filled from the amount
its own type declares, so a profile missing one of them raises before the browser opens. `--salary clt|pj|internship`
overrides that choice; it names one of the values above and never carries an amount, so only
a figure the profile already declares can reach a form. A missing field raises
`INVALID_INPUT` before the browser opens — an application cannot be un-sent.

## HTTP settings

```yaml
http:
  user_agent: "job-hunter-ai/0.1 (+https://github.com/NavesDev/job-hunter-ai)"
  timeout_seconds: 30
  min_request_interval_seconds: 1.0
```

Everything here is optional: with no file at all, the source collects the unfiltered
listing at the default pace. A platform credential never goes in this file — it would go
in `.env` with a `GEEKHUNTER_` prefix, and this platform needs none
([ADR-0003](../adr/0003-config-credentials-separation.md)).

## When the platform changes

The source raises `SOURCE_ERROR` rather than returning fewer jobs: a missing `ItemList`,
a missing `JobPosting`, a job with no title or no company, an empty listing. That error
means the page changed shape — re-record the fixtures deliberately, and let the diff be
the evidence.

One `404` is not that error: past its last page GeekHunter answers `404` instead of an
empty listing, and a filtered listing is often shorter than `--max-length` asks for. That
is the end of the listing, so the run returns the jobs it collected. A `404` on the first
page still raises — there the listing itself is gone.
