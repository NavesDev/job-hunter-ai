# The scoring model behind `score-job`

`score-job` answers one question: **what does a company's screening robot see when it
reads this résumé for this job?** Not whether the candidate is a good fit — a keyword
matcher cannot know that, and neither can this command.

Everything here is deterministic and AI-free ([ARCHITECTURE.md](ARCHITECTURE.md)): the same
PDF and the same posting always produce the same number. Every rule is written down below,
so a surprising score can always be traced back to a line of this document.

## Why the real PDF

The résumé is read from the very file the company receives (`application.resume_path`),
not from a curated list of skills. That is the whole point: if the PDF is a scan, or its
layout defeats the text extractor, the score collapses — exactly as it does in a real ATS.
A file with no extractable text raises `RESUME_ERROR` instead of scoring zero silently.

## What real ATS score

The weights below follow the public consensus on how the large platforms (Workday, Taleo,
iCIMS, Greenhouse, Lever) rank an application:

- **Keywords dominate**, usually cited at 40–50% of the score, and the *required*
  qualifications weigh more than the *preferred* ones.
- **Knockouts** — minimum years of experience, a certification, work authorization —
  reject the application regardless of everything else.
- **Parseability and section completeness** count: a résumé the parser reads badly loses
  points no matter what it says.
- The base formula is `matched / required`, with ≥80% read as a strong match and <50% as
  deprioritized.

Sources: [How ATS Scores Resumes](https://resumegyani.in/ats-guides/how-ats-scores-resumes),
[How Your Resume Score Is Actually Calculated (2026)](https://resumegyani.in/ats-guides/ats-scoring-factors-explained),
[ATS Resume Best Practices 2026](https://resumeoptimizerpro.com/blog/ats-friendly-resume-tips),
[How Workday, Greenhouse & Taleo Read Your Resume](https://www.shashiworks.com/ats-workday-greenhouse-taleo.html),
[How ATS Systems Work in 2026](https://www.atscvchecker.pro/blog/how-ats-systems-work-2026/),
[ats-screener](https://github.com/sunnypatell/ats-screener).

## The weights

Declared in `domain/matching/ats_scorer.py` as `WEIGHTS`, and summing to 100:

| Component | Weight | How it is computed |
|---|---:|---|
| `required_skills` | 45 | share of the posting's must-haves mentioned in the résumé |
| `preferred_skills` | 10 | same, over the nice-to-haves |
| `title_alignment` | 10 | share of the job title's words (minus stopwords) found in the résumé |
| `experience` | 20 | `min(1, detected months / required months)`; no requirement scores 100 |
| `parseability` | 10 | extracted characters against `700` per page, capped at 100 |
| `sections` | 5 | share of the five expected sections the résumé names |

`score` is their weighted average. The verdict is `strong` (≥ 80), `moderate` (≥ 60),
`weak` (≥ 40) or `poor` — and `knockout` whenever a hard filter fails, whatever the number.

An empty requirement list scores 100, never 0: a posting that asks for nothing cannot be
missing anything.

## Matching a term

Both sides go through the same normalization (`domain/matching/normalizer.py`): casefolded,
accents stripped, punctuation collapsed — `Experiência` and `experiencia` are the same
word. `+`, `#` and `.` survive, because `C#`, `C++` and `.NET` need them.

A term matches only as a **whole phrase**: `React` does not match `Reactive`, and
`Casos de Teste Automatizados` only counts when the four words appear together.

### Aliases

A robot compares strings, so it needs a table of the spellings it should treat as one
(`domain/matching/aliases.py`): `js`/`javascript`, `ts`/`typescript`, `node`/`node.js`,
`postgres`/`psql`/`postgresql`, `c#`/`csharp`, `.net`/`dotnet`, `k8s`/`kubernetes`,
`gcp`, `golang`, `mongo`, `react`/`reactjs`, `vue`/`vuejs`, `angular`, `next.js`,
`restful`/`rest`. A trailing plural is folded away too (`APIs` = `API`), except where the
`s` belongs to the word (`nodejs`, `access`, `status`).

The table is applied to the posting and to the résumé alike, so it can only make both sides
agree — never one of them wrong. Anything not listed has to match literally, which is also
what happens in the real systems.

## Experience

Months of experience never come from a sentence like "8 years of experience" — that is a
claim, not something a parser can check. They come from the date ranges of the positions
(`domain/matching/experience.py`): `01/2019 - 03/2021`, `jan/2020 – atual`,
`desde 12/2025`, `2019 - 2023`. Overlapping positions are counted once, and a range that
runs past today is clipped to today.

Only the **experience section** is read. A degree that ran from 2022 to 2024 is not two
years of work, and counting it would inflate every junior résumé. The section starts at an
unambiguous heading (`Experiência Profissional`, `Work Experience`, …) and ends at the next
section heading; a résumé that names no such heading is read whole.

## Requirements

Each source publishes its requirements differently, so reading them is a strategy resolved
by the job's `source` (`infra/requirements/registry.py`):

- **geekhunter** — the must-haves come from the posting's `skills` field and from the
  `Requisitos` list of the description; the nice-to-haves from `Conhecimentos Desejáveis`
  (a term listed as desirable is removed from the must-haves, since `skills` repeats it);
  the seniority from `experienceRequirements.monthsOfExperience`. Full platform notes in
  [sources/geekhunter.md](sources/geekhunter.md).
- **anything else** — the description is split into terms, all treated as must-haves, which
  is how a keyword-only ATS reads an unstructured posting.

Postings write sentences, not keywords, so each listed line is reduced to the skill inside
it. When a platform emphasizes the skill within the sentence — `Conhecimento em
**Spring Boot**` — only the emphasized part is kept; otherwise the filler around it is
trimmed (`Conhecimento em`, `Vivência com`, `Java 8 ou superior` becomes `Java`), and lines
joined by `e` or `e/ou` are split into one term each.

Three things are always dropped: a phrase longer than six words (that is prose, not a
keyword), the `N+ anos de experiência` line — the seniority requirement, already scored on
its own — and anything that is an address rather than a skill (an email, a URL).

## Knockouts

Today there is one: `min_experience`, failed when the résumé shows fewer months than the
posting demands. A failed knockout sets `verdict: "knockout"` but **does not** zero the
score — the caller still sees how close the rest was, and decides what to do.

## What the model does not do

- It does not read years per individual skill ("5+ years with React"): only the total.
- It does not see layout. Columns, tables and icons hurt a real parser; here they only show
  up indirectly, through how much text could be extracted.
- It does not judge relevance, seniority of the work, or how recent it is.
- It does not decide whether to apply. That belongs to the orchestrating agent.
