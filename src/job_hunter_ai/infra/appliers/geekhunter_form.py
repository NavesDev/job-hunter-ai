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

import time
from pathlib import Path
from typing import Any

from job_hunter_ai.domain.entities.application_result import ApplicationResult, ApplicationStatus
from job_hunter_ai.domain.entities.candidate_profile import CandidateProfile
from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.errors import ApplierError, InvalidInputError
from job_hunter_ai.domain.time_utils import utc_now
from job_hunter_ai.infra.appliers import geekhunter_diagnostics as diagnostics
from job_hunter_ai.infra.appliers import geekhunter_salary as salary
from job_hunter_ai.infra.appliers import geekhunter_screening as screening

FORM_SELECTOR = "form:has(input[name='name'])"
SUBMIT_SELECTOR = "button[type='submit']"
CONFIRMATION_TEXT = "Candidatura Completa"
SCREENING_TEXT = "Você está quase terminando"
_SCREENING_FIELD = "screening-"
RESUME_UPLOADED_TEXT = "carregado com sucesso"
SALARY_FIELD_PREFIX = "salaryExpectation"
REQUIRED_EXTRA_FIELDS = ("phone", "linkedin")
DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_DIAGNOSTICS_DIR = Path("config/local/diagnostics")
_POLL_MS = 250


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
        self._diagnostics_dir = Path(settings.get("diagnostics_dir") or DEFAULT_DIAGNOSTICS_DIR)

    def apply(self, job: Job, profile: CandidateProfile, **options: Any) -> ApplicationResult:
        url = self._checked_url(job)
        values = self._checked_values(profile)
        salaries = salary.require_any(profile.extra_fields)
        chosen = salary.require_choice(salaries, options.get("salary"))
        resume = self._checked_resume(profile)
        self._checked_consent()
        questions = screening.asked(job.raw)
        answers = self._checked_answers(questions, options.get("answers"))
        filled = self._drive(url, values, resume, salaries, chosen, answers)
        return self._result(job, filled)

    def _checked_answers(self, questions: list[dict[str, Any]], given: Any) -> dict[str, str]:
        """Every screening answer is settled before the browser opens, or none is.

        A mandatory question found on the screen with the form already submitted leaves
        the candidacy half-made, so it is a `--answer` missing here, not a failure there.
        """
        if not self._submit:
            return {}  # a dry run never reaches the screening screen
        return screening.answers_for(questions, given)

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
            "email": profile.contact_email.strip(),
            "phone": str(profile.extra_fields["phone"]).strip(),
            "linkedin": str(profile.extra_fields["linkedin"]).strip(),
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

    def _drive(
        self,
        url: str,
        values: dict[str, str],
        resume: Path,
        salaries: dict[str, str],
        chosen: str | None,
        answers: dict[str, str],
    ) -> dict[str, str]:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright

        try:
            with sync_playwright() as playwright:
                context = self._context(playwright)
                page = context.new_page()
                page.set_default_timeout(self._timeout_ms)
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    values["salary"] = self._fill(page, values, resume, salaries, chosen)
                    if self._submit:
                        self._submit_and_confirm(page, url, values, answers)
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

    def _fill(
        self,
        page: Any,
        values: dict[str, str],
        resume: Path,
        salaries: dict[str, str],
        chosen: str | None,
    ) -> str:
        form = page.locator(FORM_SELECTOR)
        if form.count() == 0:
            raise ApplierError(f"no application form on {page.url}; the page changed shape")
        # The resume goes first: uploading it re-renders the form and wipes whatever was
        # typed before, so filling the fields first would submit an empty application.
        self._upload_resume(page, form, resume)
        form.locator("input[name='name']").fill(values["name"])
        self._fill_email(form, values["email"])
        self._fill_phone(form, values["phone"])
        form.locator("input[name='linkedin']").fill(values["linkedin"])
        filled_salary = self._fill_salary(form, salaries, chosen)
        checkbox = form.locator("input[type='checkbox']")
        if self._submit and checkbox.count() and not checkbox.first.is_checked():
            # The terms box is a design-system checkbox: the real input is clipped to a
            # single pixel behind a styled control, so `check()` never settles on it and
            # even a forced click lands on whatever covers that pixel. Dispatching the
            # event on the element itself reaches the input the form actually reads.
            checkbox.first.dispatch_event("click")
            if not checkbox.first.is_checked():
                raise ApplierError(
                    "could not tick the terms checkbox; the form changed shape and an "
                    "application must never go out without it"
                )
        self._checked_form(form, values)
        return filled_salary

    def _upload_resume(self, page: Any, form: Any, resume: Path) -> None:
        """Attach the file and wait for the upload the platform runs behind it.

        The page hydrates after it loads, and a file dropped on the input before that
        happens reaches no handler at all — silently, with the form still asking for a
        resume. Settling the network first is what makes the attachment stick.
        """
        page.wait_for_load_state("networkidle")
        form.locator("input[type='file']").set_input_files(str(resume))
        try:
            page.get_by_text(RESUME_UPLOADED_TEXT).first.wait_for(timeout=self._timeout_ms)
        except Exception as exc:
            raise ApplierError(
                f"geekhunter never took the resume at {resume}; "
                "an application must never go out without it"
            ) from exc

    def _fill_phone(self, form: Any, phone: str) -> None:
        """The field carries a mask and its own country code, and ignores a set value.

        Typing is the only input the mask reads, and the digits it already shows are the
        country code it adds itself — sending them again shifts the whole number.
        """
        field = form.locator("input[name='phone']").first
        already = _digits(field.input_value())
        digits = _digits(phone)
        if already and digits.startswith(already):
            digits = digits[len(already) :]
        field.fill("")
        field.press_sequentially(digits, delay=20)

    def _checked_form(self, form: Any, values: dict[str, str]) -> None:
        """Nothing goes out half-filled: what the form holds must be what was asked for."""
        empty = [
            field
            for field in ("name", "email", "phone", "linkedin")
            if not _digits_or_text(form, field)
        ]
        if empty:
            raise ApplierError(
                f"the form dropped the values for {', '.join(empty)} before submitting; "
                "an application must never go out incomplete"
            )
        typed = _digits(form.locator("input[name='phone']").first.input_value())
        if _digits(values["phone"]) not in typed and typed not in _digits(values["phone"]):
            raise ApplierError(
                f"the form holds the phone as `{typed}`, not `{_digits(values['phone'])}`; "
                "an application must never go out with the wrong number"
            )

    def _fill_email(self, form: Any, contact_email: str) -> None:
        """Only an anonymous page asks for the address: a session fills it and locks the field.

        GeekHunter identifies the candidate by email, so applying needs no login at all —
        which is exactly why this applier never asks for one. The anonymous form asks for
        the address twice and refuses to submit until both match, so the confirmation
        field is filled from the same value.
        """
        field = form.locator("input[name='email']")
        if field.count() == 0 or field.first.is_disabled():
            return
        if field.first.input_value().strip():
            return
        if not contact_email:
            raise InvalidInputError(
                "this page has no GeekHunter session, so the form asks for your email; "
                "set candidate.contact_email in config/local/config.yaml"
            )
        field.first.fill(contact_email)
        confirmation = form.locator("input[name='confirmEmail']")
        if confirmation.count():
            confirmation.first.fill(contact_email)

    def _fill_salary(self, form: Any, salaries: dict[str, str], chosen: str | None) -> str:
        """The field name carries the contract type (`salaryExpectation.CLT`, `.PJ`, ...)."""
        field = form.locator(f"input[name^='{SALARY_FIELD_PREFIX}']")
        if field.count() == 0:
            raise ApplierError("the application form has no expected-salary field")
        field_name = str(field.first.get_attribute("name") or SALARY_FIELD_PREFIX)
        value = salary.for_field(salaries, field_name, chosen)
        field.first.fill(value)
        return value

    def _submit_and_confirm(
        self, page: Any, url: str, values: dict[str, str], answers: dict[str, str]
    ) -> None:
        """Wait for the platform's own word, and tell the two answers it can give apart.

        A form GeekHunter accepts does not always end the application: a job with
        screening questions answers with them instead of the confirmation, and the
        candidacy sits unfinished until they are answered. That is not the same failure
        as a form that was refused, and it must not read like one.
        """
        page.locator(SUBMIT_SELECTOR).first.click()
        confirmation = page.get_by_text(CONFIRMATION_TEXT).first
        screen = page.get_by_text(SCREENING_TEXT).first
        deadline = time.monotonic() + self._timeout_ms / 1000
        while time.monotonic() < deadline:
            if diagnostics.is_showing(confirmation):
                return
            if diagnostics.is_showing(screen):
                self._answer_screening(page, url, answers)
                return self._confirmed(page, url, values)
            page.wait_for_timeout(_POLL_MS)
        raise ApplierError(diagnostics.unconfirmed(page, url, values, self._diagnostics_dir))

    def _confirmed(self, page: Any, url: str, values: dict[str, str]) -> None:
        """The platform's own word on the second step, waited for exactly like the first."""
        try:
            page.get_by_text(CONFIRMATION_TEXT).first.wait_for(timeout=self._timeout_ms)
        except Exception as exc:
            raise ApplierError(
                diagnostics.unconfirmed(page, url, values, self._diagnostics_dir)
            ) from exc

    def _answer_screening(self, page: Any, url: str, answers: dict[str, str]) -> None:
        """Type the answers the caller gave, and refuse to submit a question left blank.

        Nothing is invented for a field the page shows and `--answer` did not cover: a
        screening answer is a claim about the candidate, and a wrong one is worse than
        an application that stops here.
        """
        if not answers:
            raise ApplierError(diagnostics.screening(page, url, self._diagnostics_dir))
        for identifier, answer in answers.items():
            field = page.locator(f"[name='{_SCREENING_FIELD}{identifier}']").first
            if not diagnostics.is_showing(field):
                raise ApplierError(
                    f"geekhunter asks a screening question this page does not name as "
                    f"`{_SCREENING_FIELD}{identifier}`; the questions changed shape and "
                    f"nothing was answered. "
                    f"{diagnostics.saved_page(page, url, self._diagnostics_dir)}"
                )
            field.fill(answer)
        page.locator(SUBMIT_SELECTOR).first.click()

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


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _digits_or_text(form: Any, field: str) -> str:
    locator = form.locator(f"input[name='{field}']")
    return locator.first.input_value().strip() if locator.count() else ""


def _summary(values: dict[str, str]) -> str:
    return ", ".join(f"{field}={value}" for field, value in values.items())


def _first_line(exc: Exception) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__
