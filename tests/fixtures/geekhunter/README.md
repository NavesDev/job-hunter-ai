# GeekHunter fixtures

Recorded from the live site on 2026-09-05 and **trimmed**: each file keeps the
`application/ld+json` block the parser reads, the job anchors and the pagination
anchors, and drops the ~300 KB of markup, styles and RSC payload around them.
The kept fragments are byte-for-byte what the site served.

No test in this suite reaches the network — see [TESTING.md](../../../docs/TESTING.md).

| File | What it stands for |
|---|---|
| `listing-page-1.html` | `/pt/vagas`, first page, 10 jobs |
| `listing-page-2.html` | `/pt/vagas?page=2`, the next 10 |
| `listing-empty.html` | a listing that returns no job at all |
| `job-detail-1.html` … `job-detail-3.html` | job detail pages with their `JobPosting` block |
| `job-detail-without-json-ld.html` | a detail page whose `JobPosting` block vanished (the site changed shape) |
| `job-with-form.html` | **not a recording** — the application form as an anonymous visitor sees it |
| `job-with-form-logged-in.html` | the same form as a signed-in candidate sees it: email filled and locked |

`job-with-form.html` is the one file here that was written rather than recorded. It
mirrors the real form — same field names, same required fields, same `accept=".pdf"`, same
submit label, same confirmation copy — but replaces GeekHunter's Server Action with a few
lines of local JavaScript. That is what lets the applier be driven end to end, submit
included, without an application ever leaving the machine.

Re-recording is a manual, deliberate act: it means the platform changed, and the
diff is the evidence.
