from pydantic import Field

from shared.profiling_schema import (
    Education,
    EducationBase,
    Experience,
    ExperienceBase,
    RoleTitles,
    RoleTitlesBase,
    StrengthFeatureList,
    StrengthFeatureListBase,
    TechnicalExperience,
    TechnicalExperienceBase,
)
from shared.types import ForbidExtra


class CandidateProfileRead(ForbidExtra):
    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)
    experience: Experience = Field(default_factory=Experience)
    technical_experience: TechnicalExperience = Field(default_factory=TechnicalExperience)
    languages: StrengthFeatureList = Field(default_factory=list)
    domain_background: StrengthFeatureList = Field(default_factory=list)


class CandidateProfileUpdate(ForbidExtra):
    role_titles: RoleTitlesBase
    education: EducationBase = Field(default_factory=EducationBase)
    experience: ExperienceBase = Field(default_factory=ExperienceBase)
    technical_experience: TechnicalExperienceBase = Field(
        default_factory=TechnicalExperienceBase
    )
    languages: StrengthFeatureListBase = Field(default_factory=list)
    domain_background: StrengthFeatureListBase = Field(default_factory=list)


__all__ = [
    "CandidateProfileRead",
    "CandidateProfileUpdate",
]
