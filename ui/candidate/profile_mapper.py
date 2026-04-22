from __future__ import annotations

from collections.abc import Mapping

from ui.shared.profile_types import (
    SupportedCandidateProfile,
    SupportedEducation,
    SupportedExperience,
    SupportedRoleTitles,
    SupportedStrengthFeature,
    SupportedTechnicalExperience,
)


def map_candidate_profile(source: Mapping[str, object]) -> SupportedCandidateProfile:
    return SupportedCandidateProfile(
        role_titles=_map_role_titles(_require_mapping(source, "role_titles")),
        education=_map_education(_require_mapping(source, "education")),
        experience=_map_experience(_require_mapping(source, "experience")),
        technical_experience=_map_technical_experience(
            _require_mapping(source, "technical_experience")
        ),
        languages=_map_strength_feature_list(source, "languages"),
        domain_background=_map_strength_feature_list(source, "domain_background"),
    )


def _map_role_titles(source: Mapping[str, object]) -> SupportedRoleTitles:
    return SupportedRoleTitles(
        primary=_require_str(source, "primary"),
        alternatives=_require_str_list(source, "alternatives"),
        confidence=_require_float(source, "confidence"),
        evidence=_require_str_list(source, "evidence"),
    )


def _map_education(source: Mapping[str, object]) -> SupportedEducation:
    return SupportedEducation(
        min_level=_require_optional_str(source, "min_level"),
        accepted_fields=_require_str_list(source, "accepted_fields"),
        confidence=_require_float(source, "confidence"),
        evidence=_require_str_list(source, "evidence"),
    )


def _map_experience(source: Mapping[str, object]) -> SupportedExperience:
    return SupportedExperience(
        min_years=_require_optional_int(source, "min_years"),
        seniority_band=_require_optional_str(source, "seniority_band"),
        confidence=_require_float(source, "confidence"),
        evidence=_require_str_list(source, "evidence"),
    )


def _map_strength_feature(source: Mapping[str, object]) -> SupportedStrengthFeature:
    return SupportedStrengthFeature(
        name=_require_str(source, "name"),
        strength=_require_str(source, "strength"),
        confidence=_require_float(source, "confidence"),
        evidence=_require_str_list(source, "evidence"),
    )


def _map_strength_feature_list(
    source: Mapping[str, object],
    field_name: str,
) -> list[SupportedStrengthFeature]:
    value = _require_list(source, field_name)

    result: list[SupportedStrengthFeature] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise TypeError(f"{field_name}[{index}] must be an object")
        result.append(_map_strength_feature(item))
    return result


def _map_technical_experience(
    source: Mapping[str, object],
) -> SupportedTechnicalExperience:
    return SupportedTechnicalExperience(
        technical_core_features=_map_strength_feature_list(
            source, "technical_core_features"
        ),
        technologies=_map_strength_feature_list(source, "technologies"),
    )


def _require_value(source: Mapping[str, object], field_name: str) -> object:
    if field_name not in source:
        raise KeyError(f"Missing required field: {field_name}")
    return source[field_name]


def _require_mapping(
    source: Mapping[str, object],
    field_name: str,
) -> Mapping[str, object]:
    value = _require_value(source, field_name)
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return value


def _require_list(source: Mapping[str, object], field_name: str) -> list[object]:
    value = _require_value(source, field_name)
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_str(source: Mapping[str, object], field_name: str) -> str:
    value = _require_value(source, field_name)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_optional_str(source: Mapping[str, object], field_name: str) -> str | None:
    value = _require_value(source, field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or null")
    return value


def _require_optional_int(source: Mapping[str, object], field_name: str) -> int | None:
    value = _require_value(source, field_name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer or null")
    return value


def _require_float(source: Mapping[str, object], field_name: str) -> float:
    value = _require_value(source, field_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number")
    return float(value)


def _require_str_list(source: Mapping[str, object], field_name: str) -> list[str]:
    value = _require_list(source, field_name)

    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise TypeError(f"{field_name}[{index}] must be a string")
        result.append(item)
    return result
