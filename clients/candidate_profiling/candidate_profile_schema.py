from __future__ import annotations

from typing import List

from pydantic import Field, field_validator

from shared.profiling_schema import (
    Education,
    Experience,
    RoleTitles,
    StrengthFeature,
    normalize_feature_list,
)
from shared.types import ForbidExtra

class TechnicalExperience(ForbidExtra):
    technical_core_features: List[StrengthFeature] = Field(default_factory=list)
    technologies: List[StrengthFeature] = Field(default_factory=list)

    @field_validator(
        "technical_core_features",
        "technologies",
        mode="after",
    )
    @classmethod
    def validate_feature_lists(
        cls,
        values: List[StrengthFeature],
    ) -> List[StrengthFeature]:
        return normalize_feature_list(values)


class CandidateProfile(ForbidExtra):
    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)
    experience: Experience = Field(default_factory=Experience)
    technical_experience: TechnicalExperience = Field(default_factory=TechnicalExperience)
    languages: List[StrengthFeature] = Field(default_factory=list)
    domain_background: List[StrengthFeature] = Field(default_factory=list)

    @field_validator(
        "languages",
        "domain_background",
        mode="after",
    )
    @classmethod
    def validate_feature_lists(
        cls,
        values: List[StrengthFeature],
    ) -> List[StrengthFeature]:
        return normalize_feature_list(values)


__all__ = ["CandidateProfile", "StrengthFeature", "TechnicalExperience"]
