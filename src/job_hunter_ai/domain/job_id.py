"""The job identity rule from docs/DATA_MODEL.md#job-identity.

Deterministic by construction: the same input always produces the same id, which
is what makes `list-jobs` idempotent and lets `apply-job` address a job by id.
"""

import hashlib

HASH_LENGTH = 12
_SEPARATOR = "\x1f"


def build_job_id(
    source: str,
    *,
    external_id: str | None = None,
    url: str | None = None,
    company: str | None = None,
    title: str | None = None,
) -> str:
    """Return `"<source>:<hash12>"` for the first available natural key.

    Natural key precedence: `external_id`, then `url`, then `company` + `title`.
    Raises ValueError when none of them is usable — an unidentifiable job is a
    programming error, not a runtime condition to recover from.
    """
    natural_key = _natural_key(external_id=external_id, url=url, company=company, title=title)
    digest = hashlib.sha256(natural_key.encode("utf-8")).hexdigest()[:HASH_LENGTH]
    return f"{_normalize(source)}:{digest}"


def _natural_key(
    *, external_id: str | None, url: str | None, company: str | None, title: str | None
) -> str:
    if external_id and external_id.strip():
        return _normalize(external_id)
    if url and url.strip():
        return _normalize(url)
    if company and company.strip() and title and title.strip():
        return _SEPARATOR.join((_normalize(company), _normalize(title)))
    raise ValueError("a job needs an external_id, a url, or both a company and a title")


def _normalize(value: str) -> str:
    return value.strip().lower()
