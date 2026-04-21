from __future__ import annotations

from typing import Optional

from pydantic import Field, model_validator

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
from shared.error_helpers import raise_no_updates
from shared.types import ForbidExtra


class CandidateProfileRead(ForbidExtra):
    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)
    experience: Experience = Field(default_factory=Experience)
    technical_experience: TechnicalExperience = Field(
        default_factory=TechnicalExperience
    )
    languages: StrengthFeatureList = Field(default_factory=list)
    domain_background: StrengthFeatureList = Field(default_factory=list)


class CandidateProfileUpdate(ForbidExtra):
    role_titles: Optional[RoleTitlesBase] = None
    education: Optional[EducationBase] = None
    experience: Optional[ExperienceBase] = None
    technical_experience: Optional[TechnicalExperienceBase] = None
    languages: Optional[StrengthFeatureListBase] = Field(default=None)
    domain_background: Optional[StrengthFeatureListBase] = Field(default=None)

    def has_updates(self) -> bool:
        fields = [
            self.role_titles,
            self.education,
            self.experience,
            self.technical_experience,
            self.languages,
            self.domain_background,
        ]
        return any(field is not None for field in fields)

    @model_validator(mode="after")
    def validate_has_updates(self) -> "CandidateProfileUpdate":
        if not self.has_updates():
            raise_no_updates()
        return self


class CandidateProfileCreate(ForbidExtra):
    role_titles: RoleTitlesBase
    education: EducationBase
    experience: ExperienceBase
    technical_experience: TechnicalExperienceBase
    languages: StrengthFeatureListBase
    domain_background: StrengthFeatureListBase


__all__ = [
    "CandidateProfileCreate",
    "CandidateProfileRead",
    "CandidateProfileUpdate",
]
