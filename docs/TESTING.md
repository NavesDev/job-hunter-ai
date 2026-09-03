# Testing standards

## Framework

`pytest`. No external mocking library beyond the stdlib `unittest.mock`, unless there is a real need.

## The AAA pattern is mandatory

Every test is split into 3 commented blocks, always in this order, always with these comments:

```python
def test_apply_job_should_return_skipped_when_no_applier_registered():
    # Arrange
    job = build_job(source="unknown-platform")
    use_case = ApplyJobUseCase(appliers={}, repo=FakeJobRepository())

    # Act
    result = use_case.execute(job_id=job.id, method="form")

    # Assert
    assert result.status == "skipped"
```

One `Arrange`/`Act`/`Assert` per test. A test that needs more than one `Act` should usually be two tests.

## Layout

```
tests/
├── unit/           domain/ and application/, mocked or faked ports, no real I/O
├── integration/    infra/ against real dependencies (SQLite in a temp file, local fake SMTP)
└── cli/            commands through Typer's CliRunner, checking stdout/stderr/exit code against CONTRACT.md
```

- **unit**: fast, always runs. Uses fakes or mocks of `JobSource`, `JobApplier`, `JobRepository` (simple implementations in `tests/fakes/`, not a generic `Mock()` when behavior matters).
- **integration**: proves that a concrete implementation (`SqliteJobRepository`, `EmailApplier`) honors its port's contract. Uses a real database and SMTP server, but local and ephemeral — never a real external network.
- **cli**: guarantees that the output JSON matches the [contract](CONTRACT.md) — fields, types, exit codes.

## Coverage rule

Every new piece of code in `domain/`, `application/` or `infra/` requires a test in the same PR — no test, no merge. `cli/` (pure parsing) may have lighter coverage, but each command's happy path needs at least one test in `tests/cli/`.

## Naming

`test_<unit>_should_<expected_behavior>_when_<condition>` — the test name is the specification, and should make the failure understandable from the CI output alone, without opening the file.

Example: `test_apply_job_should_return_skipped_when_no_applier_registered`.

## Fakes vs mocks

Prefer a **fake** (a simple, real in-memory implementation of a port) over a **mock** (`Mock()`/`MagicMock`) when the test depends on behavior rather than on "was called with X". A mock is fine for verifying an interaction ("SMTP was called with these parameters"); a fake is better for testing a flow ("applying twice does not duplicate the job in the repository").
