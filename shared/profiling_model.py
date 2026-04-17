from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from shared.types import ForbidExtra, SeniorityBand, Strength, SupportedField


class RoleTitles(SupportedField):
    primary: str
    alternatives: List[str] = Field(default_factory=list)


class Education(SupportedField):
    min_level: Optional[str] = None
    accepted_fields: List[str] = Field(default_factory=list)


class Experience(SupportedField):
    min_years: Optional[int] = None
    seniority_band: Optional[SeniorityBand] = None


class StrengthFeature(SupportedField):
    name: str
    strength: Strength


class TechnicalExperience(ForbidExtra):
    technical_core_features: List[StrengthFeature] = Field(default_factory=list)
    technologies: List[StrengthFeature] = Field(default_factory=list)


__all__ = [
    "Education",
    "Experience",
    "ForbidExtra",
    "RoleTitles",
    "SeniorityBand",
    "Strength",
    "StrengthFeature",
    "SupportedField",
    "TechnicalExperience",
]
