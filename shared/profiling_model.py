from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


SeniorityBand = Literal["junior", "standard", "senior", "lead", "principal"]
Strength = Literal["core", "strong", "secondary", "exposure"]


class SupportedField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)


class RoleTitles(SupportedField):
    model_config = ConfigDict(extra="forbid")

    primary: str
    alternatives: List[str] = Field(default_factory=list)


class Education(SupportedField):
    model_config = ConfigDict(extra="forbid")

    min_level: Optional[str] = None
    accepted_fields: List[str] = Field(default_factory=list)


class Experience(SupportedField):
    model_config = ConfigDict(extra="forbid")

    min_years: Optional[int] = None
    seniority_band: Optional[SeniorityBand] = None


class StrengthFeature(SupportedField):
    model_config = ConfigDict(extra="forbid")

    name: str
    strength: Strength


class TechnicalExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_core_features: List[StrengthFeature] = Field(default_factory=list)
    technologies: List[StrengthFeature] = Field(default_factory=list)


__all__ = [
    "Education",
    "Experience",
    "RoleTitles",
    "SeniorityBand",
    "Strength",
    "StrengthFeature",
    "SupportedField",
    "TechnicalExperience",
]