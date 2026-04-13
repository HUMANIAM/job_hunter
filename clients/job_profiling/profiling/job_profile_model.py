from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from shared.profiling import (
    ClassifiedTexts,
    Education,
    Experience,
    LegalAndComplianceConstraints,
    MobilityConstraints,
    RequirementTexts,
    RoleTitles,
    WorkModeConstraints,
)


class TechnicalExperience(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_core_features: ClassifiedTexts = Field(default_factory=ClassifiedTexts)
    technologies: ClassifiedTexts = Field(default_factory=ClassifiedTexts)


class VacancyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)
    experience: Experience = Field(default_factory=Experience)
    languages: ClassifiedTexts = Field(default_factory=ClassifiedTexts)
    technical_experience_requirements: TechnicalExperience = Field(
        default_factory=TechnicalExperience
    )
    domain_or_industry_requirements: RequirementTexts = Field(
        default_factory=RequirementTexts
    )
    work_mode_constraints: WorkModeConstraints = Field(
        default_factory=WorkModeConstraints
    )
    mobility_constraints: MobilityConstraints = Field(
        default_factory=MobilityConstraints
    )
    legal_and_compliance_constraints: LegalAndComplianceConstraints = Field(
        default_factory=LegalAndComplianceConstraints
    )


__all__ = ["VacancyProfile"]
