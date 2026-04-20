from __future__ import annotations

from typing import Any

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfileRead,
    CandidateProfileUpdate,
)
from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile,
    CandidateProfileRecord,
)
from shared.profiling_model import (
    Education,
    Experience,
    RoleTitles,
    StrengthFeature,
    TechnicalExperience,
)
from shared.profiling_schema import (
    EducationBase,
    ExperienceBase,
    RoleTitlesBase,
    StrengthFeatureBase,
    TechnicalExperienceBase,
)

_USER_INPUT_EVIDENCE = ["user input"]


def _support_kwargs() -> dict[str, Any]:
    return {
        "confidence": 1.0,
        "evidence": list(_USER_INPUT_EVIDENCE),
    }


def _map_role_titles(value: RoleTitlesBase) -> RoleTitles:
    return RoleTitles(
        primary=value.primary,
        alternatives=list(value.alternatives),
        **_support_kwargs(),
    )


def _map_education(value: EducationBase) -> Education:
    return Education(
        min_level=value.min_level,
        accepted_fields=list(value.accepted_fields),
        **_support_kwargs(),
    )


def _map_experience(value: ExperienceBase) -> Experience:
    return Experience(
        min_years=value.min_years,
        seniority_band=value.seniority_band,
        **_support_kwargs(),
    )


def _map_strength_feature(value: StrengthFeatureBase) -> StrengthFeature:
    return StrengthFeature(
        name=value.name,
        strength=value.strength,
        **_support_kwargs(),
    )


def _map_strength_features(values: list[StrengthFeatureBase]) -> list[StrengthFeature]:
    return [_map_strength_feature(value) for value in values]


def _map_technical_experience(value: TechnicalExperienceBase) -> TechnicalExperience:
    return TechnicalExperience(
        technical_core_features=_map_strength_features(value.technical_core_features),
        technologies=_map_strength_features(value.technologies),
    )


def map_value(value, mapper, fallback_value):
    return mapper(value) if value is not None else fallback_value

def map_candidate_profile_update(
    value: CandidateProfileUpdate,
    existing_record: CandidateProfileRecord,
) -> CandidateProfile:
    role_titles = map_value(
        value.role_titles,
        _map_role_titles,
        existing_record.role_titles_json,
    )
    education = map_value(
        value.education,
        _map_education,
        existing_record.education_json,
    )
    experience = map_value(
        value.experience,
        _map_experience,
        existing_record.experience_json,
    )
    technical_experience = map_value(
        value.technical_experience,
        _map_technical_experience,
        existing_record.technical_experience_json,
    )
    languages = map_value(
        value.languages,
        _map_strength_features,
        existing_record.languages_json,
    )
    domain_background = map_value(
        value.domain_background,
        _map_strength_features,
        existing_record.domain_background_json,
    )

    return CandidateProfile(
        role_titles=role_titles,
        education=education,
        experience=experience,
        technical_experience=technical_experience,
        languages=languages,
        domain_background=domain_background,
    )


def _to_read_schema(record: CandidateProfileRecord) -> CandidateProfileRead:
    return CandidateProfileRead.model_validate(
        {
            "role_titles": record.role_titles_json,
            "education": record.education_json,
            "experience": record.experience_json,
            "technical_experience": record.technical_experience_json,
            "languages": record.languages_json,
            "domain_background": record.domain_background_json,
        }
    )
