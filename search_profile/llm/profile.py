from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.llm import (
    OpenAIStructuredExtractor,
    build_json_schema_example,
    load_json_file,
    load_text_file,
    render_json,
    render_template,
    require_env_value,
)

DEFAULT_SEARCH_PROFILE_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS = 3000
SEARCH_PROFILE_SCHEMA_VERSION = "2.0.0"

SCHEMA_PATH = Path(__file__).with_name("search_profile_schema.json")
SYSTEM_MESSAGE_PATH = Path(__file__).with_name("search_profile_system_message.md")
USER_TEMPLATE_PATH = Path(__file__).with_name("search_profile_user_message_template.md")

_STRENGTH_RANK = {
    "exposure": 0,
    "secondary": 1,
    "strong": 2,
    "core": 3,
}


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _dedupe_and_strip(values: Iterable[str]) -> List[str]:
    cleaned_values: List[str] = []
    seen_values: set[str] = set()

    for value in values:
        normalized = _clean_text(value)
        if not normalized:
            continue

        key = normalized.casefold()
        if key in seen_values:
            continue

        cleaned_values.append(normalized)
        seen_values.add(key)

    return cleaned_values


def _normalize_taxonomy_name(value: str) -> str:
    return _clean_text(value).lower()


def _clean_confidence_score(value: Any) -> float:
    parsed_value = value
    if isinstance(parsed_value, str):
        normalized = _clean_text(parsed_value)
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


def _merge_evidence(*groups: Iterable[str]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        merged.extend(group)
    return _dedupe_and_strip(merged)


def compute_source_text_hash(profile_text: str) -> str:
    return hashlib.sha256(profile_text.encode("utf-8")).hexdigest()


class SearchProfileEvidenceBackedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: float
    evidence: List[str]

    @field_validator("confidence", mode="before")
    @classmethod
    def clean_confidence(cls, value: Any) -> float:
        return _clean_confidence_score(value)

    @field_validator("evidence", mode="after")
    @classmethod
    def clean_evidence(cls, values: List[str]) -> List[str]:
        return _dedupe_and_strip(values)


class SearchProfileFeatureItem(SearchProfileEvidenceBackedItem):
    name: str
    strength: Literal["core", "strong", "secondary", "exposure"]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = _normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_item(self) -> "SearchProfileFeatureItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for extracted feature items")
        return self


class SearchProfileLanguageItem(SearchProfileEvidenceBackedItem):
    name: str
    level: Optional[
        Literal[
            "native",
            "fluent",
            "professional",
            "conversational",
            "basic",
            "none",
        ]
    ]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = _normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @field_validator("level", mode="before")
    @classmethod
    def clean_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = _normalize_taxonomy_name(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_item(self) -> "SearchProfileLanguageItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for extracted language items")
        return self


class SearchProfileSeniorityItem(SearchProfileEvidenceBackedItem):
    value: Optional[Literal["junior", "medior", "senior", "lead", "principal", "staff"]]

    @field_validator("value", mode="before")
    @classmethod
    def clean_value(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = _normalize_taxonomy_name(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_item(self) -> "SearchProfileSeniorityItem":
        if self.value is not None and not self.evidence:
            raise ValueError("evidence must not be empty when seniority has a value")
        return self


class SearchProfileYearsExperienceItem(SearchProfileEvidenceBackedItem):
    value: Optional[int]

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("years_experience_total.value must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_item(self) -> "SearchProfileYearsExperienceItem":
        if self.value is not None and not self.evidence:
            raise ValueError(
                "evidence must not be empty when years_experience_total has a value"
            )
        return self


class SearchProfileCandidateConstraints(SearchProfileEvidenceBackedItem):
    preferred_locations: List[str]
    excluded_locations: List[str]
    preferred_workplace_types: List[str]
    excluded_workplace_types: List[str]
    requires_visa_sponsorship: Optional[bool]
    avoid_export_control_roles: Optional[bool]
    notes: List[str]

    @field_validator(
        "preferred_locations",
        "excluded_locations",
        "preferred_workplace_types",
        "excluded_workplace_types",
        "notes",
        mode="after",
    )
    @classmethod
    def clean_list_fields(cls, values: List[str]) -> List[str]:
        return _dedupe_and_strip(values)

    @model_validator(mode="after")
    def validate_item(self) -> "SearchProfileCandidateConstraints":
        has_constraints = any(
            (
                self.preferred_locations,
                self.excluded_locations,
                self.preferred_workplace_types,
                self.excluded_workplace_types,
                self.requires_visa_sponsorship is not None,
                self.avoid_export_control_roles is not None,
                self.notes,
            )
        )
        if has_constraints and not self.evidence:
            raise ValueError("evidence must not be empty when candidate_constraints are set")
        return self


class SearchProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[SearchProfileFeatureItem]
    languages: List[SearchProfileLanguageItem]
    protocols: List[SearchProfileFeatureItem]
    standards: List[SearchProfileFeatureItem]
    domains: List[SearchProfileFeatureItem]
    seniority: SearchProfileSeniorityItem
    years_experience_total: SearchProfileYearsExperienceItem
    candidate_constraints: SearchProfileCandidateConstraints

    @field_validator("skills", "protocols", "standards", "domains", mode="after")
    @classmethod
    def dedupe_feature_items(
        cls,
        values: List[SearchProfileFeatureItem],
    ) -> List[SearchProfileFeatureItem]:
        deduped: dict[str, SearchProfileFeatureItem] = {}

        for value in values:
            existing = deduped.get(value.name)
            if existing is None:
                deduped[value.name] = value
                continue

            best_strength = (
                value.strength
                if _STRENGTH_RANK[value.strength] > _STRENGTH_RANK[existing.strength]
                else existing.strength
            )
            deduped[value.name] = SearchProfileFeatureItem(
                name=existing.name,
                strength=best_strength,
                confidence=max(existing.confidence, value.confidence),
                evidence=_merge_evidence(existing.evidence, value.evidence),
            )

        return list(deduped.values())

    @field_validator("languages", mode="after")
    @classmethod
    def dedupe_language_items(
        cls,
        values: List[SearchProfileLanguageItem],
    ) -> List[SearchProfileLanguageItem]:
        deduped: dict[str, SearchProfileLanguageItem] = {}

        for value in values:
            existing = deduped.get(value.name)
            if existing is None:
                deduped[value.name] = value
                continue

            if value.confidence > existing.confidence:
                preferred_level = value.level or existing.level
            elif existing.confidence > value.confidence:
                preferred_level = existing.level or value.level
            else:
                preferred_level = existing.level or value.level

            deduped[value.name] = SearchProfileLanguageItem(
                name=existing.name,
                level=preferred_level,
                confidence=max(existing.confidence, value.confidence),
                evidence=_merge_evidence(existing.evidence, value.evidence),
            )

        return list(deduped.values())


class SearchProfileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text_hash: str
    schema_version: str
    profile: SearchProfilePayload

    @field_validator("source_text_hash")
    @classmethod
    def validate_source_text_hash(cls, value: str) -> str:
        normalized = _clean_text(value)
        if len(normalized) != 64:
            raise ValueError("source_text_hash must be a sha256 hex digest")
        return normalized

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        normalized = _clean_text(value)
        if not normalized:
            raise ValueError("schema_version must not be empty")
        return normalized


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return load_text_file(SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_user_template() -> str:
    return load_text_file(USER_TEMPLATE_PATH)


@lru_cache(maxsize=1)
def _load_search_profile_schema() -> Dict[str, Any]:
    return load_json_file(SCHEMA_PATH)


def _render_llm_output_schema_json() -> str:
    root_schema = _load_search_profile_schema()
    profile_schema = root_schema["$defs"]["searchProfile"]
    return render_json(build_json_schema_example(profile_schema, root_schema))


def _render_candidate_context_json(candidate_context: Any) -> str:
    return render_json(candidate_context)


def render_search_profile_user_message(
    profile_text: str,
    *,
    candidate_context: Any | None = None,
) -> str:
    template = _load_user_template()
    return render_template(
        template,
        {
            "{{search_profile_schema_json}}": _render_llm_output_schema_json(),
            "{{candidate_context_json}}": _render_candidate_context_json(
                candidate_context
            ),
            "{{cv_text}}": profile_text.replace("```", "'''"),
        },
    )


def _build_extraction_payload(
    profile_text: str,
    *,
    candidate_context: Any | None = None,
) -> Dict[str, Any]:
    return {
        "profile_text": profile_text,
        "candidate_context": candidate_context,
    }


def _render_user_message(payload: Dict[str, Any]) -> str:
    return render_search_profile_user_message(
        payload["profile_text"],
        candidate_context=payload.get("candidate_context"),
    )


class SearchProfileExtractor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = DEFAULT_SEARCH_PROFILE_LLM_MODEL,
        timeout_seconds: float = 60.0,
        max_completion_tokens: int = DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=SearchProfilePayload,
            system_message=_load_system_message(),
            render_user_message=_render_user_message,
            operation_name="Search profile extraction",
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
        )

    @classmethod
    def from_env(cls) -> "SearchProfileExtractor":
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Search profile extraction",
        )
        model = os.environ.get(
            "SEARCH_PROFILE_LLM_MODEL",
            DEFAULT_SEARCH_PROFILE_LLM_MODEL,
        )
        max_completion_tokens = int(
            os.environ.get(
                "SEARCH_PROFILE_LLM_MAX_COMPLETION_TOKENS",
                str(DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS),
            )
        )
        return cls(
            client=OpenAI(api_key=api_key),
            model=model,
            max_completion_tokens=max_completion_tokens,
        )

    def extract(
        self,
        profile_text: str,
        *,
        candidate_context: Any | None = None,
    ) -> SearchProfileDocument:
        profile = self._extractor.extract(
            _build_extraction_payload(
                profile_text,
                candidate_context=candidate_context,
            )
        )
        return SearchProfileDocument(
            source_text_hash=compute_source_text_hash(profile_text),
            schema_version=SEARCH_PROFILE_SCHEMA_VERSION,
            profile=profile,
        )


@lru_cache(maxsize=1)
def get_default_search_profile_extractor() -> SearchProfileExtractor:
    return SearchProfileExtractor.from_env()


def extract_profile(
    profile_text: str,
    *,
    candidate_context: Any | None = None,
    extractor: SearchProfileExtractor | None = None,
) -> SearchProfileDocument:
    active_extractor = extractor or get_default_search_profile_extractor()
    return active_extractor.extract(
        profile_text,
        candidate_context=candidate_context,
    )


__all__ = [
    "DEFAULT_SEARCH_PROFILE_LLM_MODEL",
    "DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS",
    "SEARCH_PROFILE_SCHEMA_VERSION",
    "SearchProfileFeatureItem",
    "SearchProfileLanguageItem",
    "SearchProfileSeniorityItem",
    "SearchProfileYearsExperienceItem",
    "SearchProfileCandidateConstraints",
    "SearchProfilePayload",
    "SearchProfileDocument",
    "SearchProfileExtractor",
    "compute_source_text_hash",
    "extract_profile",
    "get_default_search_profile_extractor",
    "render_search_profile_user_message",
]
