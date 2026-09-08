"""The extractor for any source that publishes nothing but a description.

It makes no guess about which line is a requirement: every term the description lists is
treated as a must-have, which is exactly how a keyword-only ATS reads an unstructured
posting.
"""

from job_hunter_ai.domain.entities.job import Job
from job_hunter_ai.domain.entities.job_requirements import JobRequirements
from job_hunter_ai.infra.requirements import html_text
from job_hunter_ai.infra.requirements.terms import clean_terms


class GenericRequirementsExtractor:
    """The `RequirementsExtractor` port used when a source has no structured requirements."""

    name = "generic"

    def extract(self, job: Job) -> JobRequirements:
        return JobRequirements(
            title=job.title,
            required=clean_terms(html_text.to_text(job.description)),
            preferred=(),
            months_of_experience=None,
        )
