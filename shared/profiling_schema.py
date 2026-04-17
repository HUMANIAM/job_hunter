from __future__ import annotations

from typing import Any, List, Optional

from pydantic import Field, field_validator, model_validator

from shared.normalizer import (
    dedupe_by_normalized_key,
    normalize_and_dedupe_texts,
    normalize_taxonomy_name,
    normalize_text,
)
from shared.types import ForbidExtra, SeniorityBand, Strength


def _clean_confidence_score(value: Any) -> float:
    parsed_value = value
    if isinstance(parsed_value, str):
        normalized = normalize_text(parsed_value)
        if not normalized:
            raise ValueError("confidence must not be empty")
        try:
            parsed_value = float(normalized)
        except ValueError as error:
            raise ValueError("confidence must be a number between 0 and 1") from error

    if not isinstance(parsed_value, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")

    confidence = float(parsed_value)
    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")
    return round(confidence, 4)


def _clean_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    parsed_value = value
    if isinstance(parsed_value, str):
        normalized = normalize_text(parsed_value)
        if not normalized:
            return None
        try:
            parsed_value = int(normalized)
        except ValueError as error:
            raise ValueError("value must be a non-negative integer") from error

    if not isinstance(parsed_value, int):
        raise ValueError("value must be a non-negative integer")

    if parsed_value < 0:
        raise ValueError("value must be a non-negative integer")

    return parsed_value


def _clean_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = normalize_text(value)
        if not normalized:
            return None

        if normalized in {"true", "yes", "required"}:
            return True
        if normalized in {"false", "no", "not required"}:
            return False

    raise ValueError("value must be a boolean")


def _normalize_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    normalized = normalize_taxonomy_name(value)
    if not normalized:
        return None

    return normalized


def _normalize_text_list(values: List[str]) -> List[str]:
    return normalize_and_dedupe_texts(
        normalize_taxonomy_name(value) for value in values
    )


class SupportedFieldMixin(ForbidExtra):
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value: Any) -> float:
        return _clean_confidence_score(value)

    @field_validator("evidence", mode="after")
    @classmethod
    def validate_evidence(cls, values: List[str]) -> List[str]:
        return normalize_and_dedupe_texts(values)


class RoleTitles(SupportedFieldMixin):
    primary: str
    alternatives: List[str] = Field(default_factory=list)
    confidence: float
    evidence: List[str]

    @model_validator(mode="after")
    def validate_titles(self) -> "RoleTitles":
        primary = normalize_taxonomy_name(self.primary)
        if not primary:
            raise ValueError("primary role title must not be empty")

        alternatives = [
            title
            for title in normalize_and_dedupe_texts(
                normalize_taxonomy_name(title) for title in self.alternatives
            )
            if title != primary
        ][:5]

        if not self.evidence:
            raise ValueError("evidence must not be empty")

        self.primary = primary
        self.alternatives = alternatives
        return self


class Education(SupportedFieldMixin):
    min_level: Optional[str] = None
    accepted_fields: List[str] = Field(default_factory=list)

    @field_validator("min_level", mode="before")
    @classmethod
    def validate_min_level(cls, value: Any) -> Optional[str]:
        return _normalize_optional_text(value)

    @field_validator("accepted_fields", mode="after")
    @classmethod
    def validate_accepted_fields(cls, values: List[str]) -> List[str]:
        return _normalize_text_list(values)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "Education":
        has_value = self.min_level is not None or bool(self.accepted_fields)
        if has_value and not self.evidence:
            raise ValueError(
                "evidence must not be empty when education requirements are set"
            )
        return self


class Experience(SupportedFieldMixin):
    min_years: Optional[int] = None
    seniority_band: Optional[SeniorityBand] = None

    @field_validator("min_years", mode="before")
    @classmethod
    def validate_min_years(cls, value: Any) -> Optional[int]:
        return _clean_optional_int(value)

    @field_validator("seniority_band", mode="before")
    @classmethod
    def validate_seniority_band(cls, value: Any) -> Optional[SeniorityBand]:
        return _normalize_optional_text(value)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "Experience":
        has_value = self.min_years is not None or self.seniority_band is not None
        if has_value and not self.evidence:
            raise ValueError(
                "evidence must not be empty when experience requirements are set"
            )
        return self


class StrengthFeature(SupportedFieldMixin):
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


class ClassifiedTexts(SupportedFieldMixin):
    required: List[str] = Field(default_factory=list)
    preferred: List[str] = Field(default_factory=list)

    @field_validator("required", "preferred", mode="after")
    @classmethod
    def validate_texts(cls, values: List[str]) -> List[str]:
        return _normalize_text_list(values)

    @model_validator(mode="after")
    def validate_lists(self) -> "ClassifiedTexts":
        required_set = set(self.required)
        self.preferred = [value for value in self.preferred if value not in required_set]

        has_value = bool(self.required or self.preferred)
        if has_value and not self.evidence:
            raise ValueError("evidence must not be empty when classified texts are set")

        return self


class RequirementTexts(SupportedFieldMixin):
    required: List[str] = Field(default_factory=list)

    @field_validator("required", mode="after")
    @classmethod
    def validate_required(cls, values: List[str]) -> List[str]:
        return _normalize_text_list(values)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "RequirementTexts":
        if self.required and not self.evidence:
            raise ValueError(
                "evidence must not be empty when requirement texts are set"
            )
        return self


class WorkModeConstraints(SupportedFieldMixin):
    onsite: Optional[bool] = None
    hybrid: Optional[bool] = None
    remote: Optional[bool] = None
    location: List[str] = Field(default_factory=list)

    @field_validator("onsite", "hybrid", "remote", mode="before")
    @classmethod
    def validate_bool_fields(cls, value: Any) -> Optional[bool]:
        return _clean_optional_bool(value)

    @field_validator("location", mode="after")
    @classmethod
    def validate_location(cls, values: List[str]) -> List[str]:
        return normalize_and_dedupe_texts(normalize_text(value) for value in values)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "WorkModeConstraints":
        has_value = (
            self.onsite is not None
            or self.hybrid is not None
            or self.remote is not None
            or bool(self.location)
        )
        if has_value and not self.evidence:
            raise ValueError(
                "evidence must not be empty when work mode constraints are set"
            )
        return self


class MobilityConstraints(SupportedFieldMixin):
    travel_required: Optional[bool] = None
    driving_license_required: Optional[bool] = None

    @field_validator("travel_required", "driving_license_required", mode="before")
    @classmethod
    def validate_bool_fields(cls, value: Any) -> Optional[bool]:
        return _clean_optional_bool(value)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "MobilityConstraints":
        has_value = (
            self.travel_required is not None
            or self.driving_license_required is not None
        )
        if has_value and not self.evidence:
            raise ValueError(
                "evidence must not be empty when mobility constraints are set"
            )
        return self


class LegalAndComplianceConstraints(SupportedFieldMixin):
    work_authorization_required: Optional[bool] = None
    export_control_required: Optional[bool] = None
    background_check_required: Optional[bool] = None
    security_clearance_required: Optional[bool] = None

    @field_validator(
        "work_authorization_required",
        "export_control_required",
        "background_check_required",
        "security_clearance_required",
        mode="before",
    )
    @classmethod
    def validate_bool_fields(cls, value: Any) -> Optional[bool]:
        return _clean_optional_bool(value)

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "LegalAndComplianceConstraints":
        has_value = (
            self.work_authorization_required is not None
            or self.export_control_required is not None
            or self.background_check_required is not None
            or self.security_clearance_required is not None
        )
        if has_value and not self.evidence:
            raise ValueError(
                "evidence must not be empty when legal and compliance constraints are set"
            )
        return self


__all__ = [
    "ClassifiedTexts",
    "Education",
    "Experience",
    "LegalAndComplianceConstraints",
    "MobilityConstraints",
    "RequirementTexts",
    "RoleTitles",
    "SeniorityBand",
    "Strength",
    "StrengthFeature",
    "SupportedFieldMixin",
    "WorkModeConstraints",
    "normalize_feature_list",
]
