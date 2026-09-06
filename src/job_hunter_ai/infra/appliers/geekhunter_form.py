"""Applies to a GeekHunter job through the platform's fixed form.

Why a browser lives here at all is settled in
[ADR-0005](../../../../docs/adr/0005-playwright-for-form-appliers.md): the form submits
through a Next.js Server Action whose id changes on every deploy, so driving the page is
the honest transport, not raw HTTP.

Two rules shape everything below. Submitting is irreversible, so every value is checked
*before* the browser opens — look before you leap. And an application counts as sent only
when the platform itself says so: the confirmation text is the evidence, never a
successful click.
"""

from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import ApplierError, InvalidInputError
from job_hunter_ai.domain.time_utils import utc_now

FORM_SELECTOR = "form:has(input[name='name'])"
SUBMIT_SELECTOR = "button[type='submit']"
CONFIRMATION_TEXT = "Candidatura Completa"
SALARY_FIELD_PREFIX = "salaryExpectation"
REQUIRED_EXTRA_FIELDS = ("phone", "linkedin", "salary_expectation")
DEFAULT_TIMEOUT_MS = 30_000


class GeekHunterFormApplier:
    """Fills GeekHunter's fixed application form and reports what the platform answered."""

    name = "geekhunter-form"

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self._accept_terms = bool(settings.get("accept_terms", False))
        self._submit = bool(settings.get("submit", True)) and not settings.get("dry_run", False)
        self._headless = bool(settings.get("headless", True))
        self._timeout_ms = int(settings.get("timeout_ms", DEFAULT_TIMEOUT_MS))
        self._profile_dir = settings.get("browser_profile_dir")

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        url = self._checked_url(job)
        values = self._checked_values(profile)
        resume = self._checked_resume(profile)
        self._checked_consent()
        filled = self._drive(url, values, resume)
        return self._result(job, filled)

    # --- validation: everything that can be known before the browser opens ---

    def _checked_url(self, job: Job) -> str:
        if not job.url:
            raise InvalidInputError(f"job `{job.id}` has no url to apply through")
        return job.url

    def _checked_values(self, profile: CandidateProfile) -> dict[str, str]:
        missing = [
            field
            for field in REQUIRED_EXTRA_FIELDS
            if not str(profile.extra_fields.get(field, "")).strip()
        ]
        if not profile.name.strip():
            missing.insert(0, "candidate.name")
        if missing:
            raise InvalidInputError(
                "the geekhunter form needs values this profile does not carry: "
                f"{', '.join(missing)} (config/local/config.yaml)"
            )
        return {
            "name": profile.name.strip(),
            "phone": str(profile.extra_fields["phone"]).strip(),
            "linkedin": str(profile.extra_fields["linkedin"]).strip(),
            "salary": str(profile.extra_fields["salary_expectation"]).strip(),
        }

    def _checked_resume(self, profile: CandidateProfile) -> Path:
        resume = profile.resume_path
        if not resume.is_file():
            raise InvalidInputError(f"resume not found: {resume}")
        if resume.suffix.lower() != ".pdf":
            raise InvalidInputError(f"the geekhunter form only accepts a PDF resume, got {resume}")
        return resume

    def _checked_consent(self) -> None:
        """Only a real submission accepts anything: a dry run ticks no box and asks nothing."""
        if self._submit and not self._accept_terms:
            raise InvalidInputError(
                "applying on geekhunter accepts its Privacy Policy and Terms of Use on your "
                "behalf; set `accept_terms: true` in config/local/sources/geekhunter.yaml to "
                "say so yourself"
            )

    # --- the browser ---

    def _drive(self, url: str, values: dict[str, str], resume: Path) -> dict[str, str]:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as playwright:
                context = self._context(playwright)
                page = context.new_page()
                page.set_default_timeout(self._timeout_ms)
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    self._fill(page, values, resume)
                    if self._submit:
                        self._submit_and_confirm(page, url)
                finally:
                    context.close()
        except PlaywrightError as exc:
            raise ApplierError(f"could not apply through {url}: {_first_line(exc)}") from exc
        return values

    def _context(self, playwright: Any) -> Any:
        """A persistent profile carries the session the user already logged in with."""
        if self._profile_dir:
            return playwright.chromium.launch_persistent_context(
                str(self._profile_dir), headless=self._headless
            )
        return playwright.chromium.launch(headless=self._headless).new_context()

    def _fill(self, page: Any, values: dict[str, str], resume: Path) -> None:
        form = page.locator(FORM_SELECTOR)
        if form.count() == 0:
            raise ApplierError(f"no application form on {page.url}; the page changed shape")
        form.locator("input[name='name']").fill(values["name"])
        form.locator("input[name='phone']").fill(values["phone"])
        form.locator("input[name='linkedin']").fill(values["linkedin"])
        form.locator("input[type='file']").set_input_files(str(resume))
        self._fill_salary(form, values["salary"])
        checkbox = form.locator("input[type='checkbox']")
        if self._submit and checkbox.count() and not checkbox.first.is_checked():
            checkbox.first.check()

    def _fill_salary(self, form: Any, salary: str) -> None:
        """The field name carries the contract type (`salaryExpectation.CLT`, `.PJ`, ...)."""
        field = form.locator(f"input[name^='{SALARY_FIELD_PREFIX}']")
        if field.count() == 0:
            raise ApplierError("the application form has no expected-salary field")
        field.first.fill(salary)

    def _submit_and_confirm(self, page: Any, url: str) -> None:
        page.locator(SUBMIT_SELECTOR).first.click()
        try:
            page.get_by_text(CONFIRMATION_TEXT).first.wait_for(timeout=self._timeout_ms)
        except Exception as exc:
            raise ApplierError(
                f"geekhunter never confirmed the application for {url}; "
                "the attempt may or may not have gone through"
            ) from exc

    # --- the outcome ---

    def _result(self, job: Job, values: dict[str, str]) -> ApplicationResult:
        if not self._submit:
            return ApplicationResult(
                job_id=job.id,
                method="form",
                status=ApplicationStatus.SKIPPED,
                applier=self.name,
                detail=f"dry run: form filled, nothing submitted ({_summary(values)})",
                applied_at=utc_now(),
            )
        return ApplicationResult(
            job_id=job.id,
            method="form",
            status=ApplicationStatus.SENT,
            applier=self.name,
            detail=f"geekhunter confirmed the application for `{job.title}`",
            applied_at=utc_now(),
        )


def _summary(values: dict[str, str]) -> str:
    return ", ".join(f"{field}={value}" for field, value in values.items())


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__
