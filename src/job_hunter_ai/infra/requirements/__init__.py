from job_hunter_ai.infra.requirements.geekhunter_requirements import (
    GeekHunterRequirementsExtractor,
)
from job_hunter_ai.infra.requirements.generic_requirements import GenericRequirementsExtractor
from job_hunter_ai.infra.requirements.registry import ExtractorRegistry

__all__ = [
    "ExtractorRegistry",
    "GeekHunterRequirementsExtractor",
    "GenericRequirementsExtractor",
]
