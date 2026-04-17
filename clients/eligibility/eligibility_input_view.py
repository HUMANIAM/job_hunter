from __future__ import annotations

from typing import ClassVar

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfile,
    StrengthFeature,
)
from clients.job_profiling.profiling.job_profile_model import VacancyProfile


class EligibilityInputView:
    _MISSING_VALUE: ClassVar[str] = "not specified"
    _EMPTY_ALTERNATIVES_VALUE: ClassVar[str] = "none"

    @classmethod
    def get_candidate_view(
        cls,
        candidate_profile: CandidateProfile,
    ) -> dict[str, str]:
        return {
            "{{CANDIDATE_ROLE_PRIMARY}}": candidate_profile.role_titles.primary,
            "{{CANDIDATE_ROLE_ALTERNATIVES}}": cls._format_text_list(
                candidate_profile.role_titles.alternatives,
                empty_value=cls._EMPTY_ALTERNATIVES_VALUE,
            ),
            "{{CANDIDATE_EDUCATION_MIN_LEVEL}}": (
                candidate_profile.education.min_level or cls._MISSING_VALUE
            ),
            "{{CANDIDATE_EDUCATION_FIELDS}}": cls._format_text_list(
                candidate_profile.education.accepted_fields
            ),
            "{{CANDIDATE_LANGUAGES}}": cls._format_strength_feature_list(
                candidate_profile.languages
            ),
            "{{CANDIDATE_MIN_YEARS}}": (
                str(candidate_profile.experience.min_years)
                if candidate_profile.experience.min_years is not None
                else cls._MISSING_VALUE
            ),
            "{{CANDIDATE_SENIORITY_BAND}}": (
                candidate_profile.experience.seniority_band or cls._MISSING_VALUE
            ),
            "{{CANDIDATE_TECHNICAL_CORE_FEATURES}}": cls._format_strength_feature_block(
                candidate_profile.technical_experience.technical_core_features
            ),
            "{{CANDIDATE_TECHNOLOGIES}}": cls._format_strength_feature_block(
                candidate_profile.technical_experience.technologies
            ),
        }

    @classmethod
    def get_job_view(
        cls,
        vacancy_profile: VacancyProfile,
    ) -> dict[str, str]:
        return {
            "{{VACANCY_ROLE_PRIMARY}}": vacancy_profile.role_titles.primary,
            "{{VACANCY_ROLE_ALTERNATIVES}}": cls._format_text_list(
                vacancy_profile.role_titles.alternatives,
                empty_value=cls._EMPTY_ALTERNATIVES_VALUE,
            ),
            "{{VACANCY_EDUCATION_MIN_LEVEL}}": (
                vacancy_profile.education.min_level or cls._MISSING_VALUE
            ),
            "{{VACANCY_EDUCATION_FIELDS}}": cls._format_text_list(
                vacancy_profile.education.accepted_fields
            ),
            "{{VACANCY_REQUIRED_LANGUAGES}}": cls._format_text_list(
                vacancy_profile.languages.required
            ),
            "{{VACANCY_PREFERRED_LANGUAGES}}": cls._format_text_list(
                vacancy_profile.languages.preferred
            ),
            "{{VACANCY_MIN_YEARS}}": (
                str(vacancy_profile.experience.min_years)
                if vacancy_profile.experience.min_years is not None
                else cls._MISSING_VALUE
            ),
            "{{VACANCY_SENIORITY_BAND}}": (
                vacancy_profile.experience.seniority_band or cls._MISSING_VALUE
            ),
            "{{VACANCY_TECHNICAL_CORE_FEATURES}}": cls._format_job_feature_block(
                vacancy_profile.technical_experience_requirements.technical_core_features.required,
                vacancy_profile.technical_experience_requirements.technical_core_features.preferred,
            ),
            "{{VACANCY_TECHNOLOGIES}}": cls._format_job_feature_block(
                vacancy_profile.technical_experience_requirements.technologies.required,
                vacancy_profile.technical_experience_requirements.technologies.preferred,
            ),
        }

    @classmethod
    def _format_text_list(
        cls,
        values: list[str],
        *,
        empty_value: str | None = None,
    ) -> str:
        if not values:
            return empty_value or cls._MISSING_VALUE
        return ", ".join(values)

    @classmethod
    def _format_strength_feature_list(
        cls,
        values: list[StrengthFeature],
    ) -> str:
        if not values:
            return cls._MISSING_VALUE
        return ", ".join(f"{item.name} ({item.strength})" for item in values)

    @classmethod
    def _format_strength_feature_block(
        cls,
        values: list[StrengthFeature],
    ) -> str:
        if not values:
            return cls._MISSING_VALUE
        return "\n".join(f"- {item.name} ({item.strength})" for item in values)

    @classmethod
    def _format_job_feature_block(
        cls,
        required: list[str],
        preferred: list[str],
    ) -> str:
        lines: list[str] = []
        lines.extend(f"- {value} (required)" for value in required)
        lines.extend(f"- {value} (preferred)" for value in preferred)
        if not lines:
            return cls._MISSING_VALUE
        return "\n".join(lines)


__all__ = ["EligibilityInputView"]
