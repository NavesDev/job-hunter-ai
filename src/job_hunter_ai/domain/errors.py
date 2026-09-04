"""Typed domain exceptions. Each one maps to a `code` in docs/CONTRACT.md."""


class JobHunterError(Exception):
    """Base of every project exception. `code` is the contract the external agent reads."""

    code = "INTERNAL_ERROR"


class SourceNotFoundError(JobHunterError):
    code = "SOURCE_NOT_FOUND"


class ApplierNotFoundError(JobHunterError):
    code = "APPLIER_NOT_FOUND"


class JobNotFoundError(JobHunterError):
    code = "JOB_NOT_FOUND"


class SmtpError(JobHunterError):
    code = "SMTP_ERROR"


class InvalidInputError(JobHunterError):
    code = "INVALID_INPUT"


class NotImplementedYetError(JobHunterError):
    """Temporary: the command is declared but not delivered yet. Removed in Sprint 01."""

    code = "NOT_IMPLEMENTED"
