from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FieldSupport:
    confidence: float
    evidence: list[str]


# Plain value types

@dataclass
class RoleTitles:
    primary: str
    alternatives: list[str]


@dataclass
class Education:
    min_level: str | None
    accepted_fields: list[str]


@dataclass
class Experience:
    min_years: int | None
    seniority_band: str | None


@dataclass
class StrengthFeature:
    name: str
    strength: str


@dataclass
class TechnicalExperience:
    technical_core_features: list[StrengthFeature]
    technologies: list[StrengthFeature]


@dataclass
class CandidateProfile:
    role_titles: RoleTitles
    education: Education
    experience: Experience
    technical_experience: TechnicalExperience
    languages: list[StrengthFeature]
    domain_background: list[StrengthFeature]


# Backend-supported types

@dataclass
class SupportedRoleTitles(RoleTitles, FieldSupport):
    pass


@dataclass
class SupportedEducation(Education, FieldSupport):
    pass


@dataclass
class SupportedExperience(Experience, FieldSupport):
    pass


@dataclass
class SupportedStrengthFeature(StrengthFeature, FieldSupport):
    pass


@dataclass
class SupportedTechnicalExperience:
    technical_core_features: list[SupportedStrengthFeature]
    technologies: list[SupportedStrengthFeature]


@dataclass
class SupportedCandidateProfile:
    role_titles: SupportedRoleTitles
    education: SupportedEducation
    experience: SupportedExperience
    technical_experience: SupportedTechnicalExperience
    languages: list[SupportedStrengthFeature]
    domain_background: list[SupportedStrengthFeature]
