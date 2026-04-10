from __future__ import annotations

from typing import Any, List

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


class RoleTitles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    alternatives: List[str] = Field(default_factory=list)
    confidence: float
    evidence: List[str]

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value: Any) -> float:
        return _clean_confidence_score(value)

    @field_validator("evidence", mode="after")
    @classmethod
    def validate_evidence(cls, values: List[str]) -> List[str]:
        cleaned_values = normalize_and_dedupe_texts(values)
        if not cleaned_values:
            raise ValueError("evidence must not be empty")
        return cleaned_values

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

        self.primary = primary
        self.alternatives = alternatives
        return self


class VacancyProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_titles: RoleTitles


__all__ = [
    "RoleTitles",
    "VacancyProfile",
]
