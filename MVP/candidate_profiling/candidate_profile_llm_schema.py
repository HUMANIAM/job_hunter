from __future__ import annotations

from pydantic import Field

from shared.profiling_schema import (
    Education,
    Experience,
    RoleTitles,
    StrengthFeatureList,
    TechnicalExperience,
)
from shared.types import ForbidExtra


class CandidateProfile(ForbidExtra):
    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)
    experience: Experience = Field(default_factory=Experience)
    technical_experience: TechnicalExperience = Field(default_factory=TechnicalExperience)
    languages: StrengthFeatureList = Field(default_factory=list)
    domain_background: StrengthFeatureList = Field(default_factory=list)


__all__ = ["CandidateProfile", "StrengthFeatureList", "TechnicalExperience"]
