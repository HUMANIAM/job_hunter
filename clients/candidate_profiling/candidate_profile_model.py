from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.normalizer import dedupe_by_normalized_key, normalize_taxonomy_name
from shared.profiling import Education, Experience, RoleTitles, SupportedFieldMixin

Strength = Literal["core", "strong", "secondary", "exposure"]


class StrengthFeature(SupportedFieldMixin):
    model_config = ConfigDict(extra="forbid")

    name: str
    strength: Strength

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        normalized = normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "StrengthFeature":
        if not self.evidence:
            raise ValueError("evidence must not be empty")
        return self


def normalize_feature_list(values: List[StrengthFeature]) -> List[StrengthFeature]:
    return dedupe_by_normalized_key(
        values,
        key_selector=lambda item: item.name,
    )


class TechnicalExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
