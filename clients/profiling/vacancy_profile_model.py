from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.normalizer import (
    normalize_and_dedupe_texts,
    normalize_taxonomy_name,
    normalize_text,
)


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


class _SupportedFieldMixin(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class RoleTitles(_SupportedFieldMixin):
    model_config = ConfigDict(extra="forbid")

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


class Education(_SupportedFieldMixin):
    model_config = ConfigDict(extra="forbid")

    min_level: Optional[str] = None
    accepted_fields: List[str] = Field(default_factory=list)

    @field_validator("min_level", mode="before")
    @classmethod
    def validate_min_level(cls, value: Any) -> Optional[str]:
        if value is None:
            return None

        normalized = normalize_taxonomy_name(value)
        if not normalized:
            return None

        return normalized

    @field_validator("accepted_fields", mode="after")
    @classmethod
    def validate_accepted_fields(cls, values: List[str]) -> List[str]:
        return normalize_and_dedupe_texts(
            normalize_taxonomy_name(value) for value in values
        )

    @model_validator(mode="after")
    def validate_supporting_evidence(self) -> "Education":
        has_education_requirements = self.min_level is not None or bool(
            self.accepted_fields
        )
        if has_education_requirements and not self.evidence:
            raise ValueError(
                "evidence must not be empty when education requirements are set"
            )
        return self


class VacancyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_titles: RoleTitles
    education: Education = Field(default_factory=Education)


__all__ = [
    "VacancyProfile",
]
