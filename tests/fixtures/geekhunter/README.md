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

Re-recording is a manual, deliberate act: it means the platform changed, and the
diff is the evidence.
