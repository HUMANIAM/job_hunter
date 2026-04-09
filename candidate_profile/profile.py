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
from shared.normalizer import (
    normalize_and_dedupe_texts,
    normalize_taxonomy_name,
    normalize_text,
)

DEFAULT_CANDIDATE_PROFILE_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS = 3000
CANDIDATE_PROFILE_SCHEMA_VERSION = "2.0.0"

# Backward-compatible aliases for the pre-rename API.
DEFAULT_SEARCH_PROFILE_LLM_MODEL = DEFAULT_CANDIDATE_PROFILE_LLM_MODEL
DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS = (
    DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS
)
SEARCH_PROFILE_SCHEMA_VERSION = CANDIDATE_PROFILE_SCHEMA_VERSION

PROFILE_DIR = Path(__file__).resolve().parent
LLM_DIR = PROFILE_DIR / "llm"

SCHEMA_PATH = PROFILE_DIR / "candidate_profile_schema.json"
SYSTEM_MESSAGE_PATH = LLM_DIR / "candidate_profile_system_message.md"
USER_TEMPLATE_PATH = LLM_DIR / "candidate_profile_user_message_template.md"

_STRENGTH_RANK = {
    "exposure": 0,
    "secondary": 1,
    "strong": 2,
    "core": 3,
}


def _normalize_workplace_type(value: str) -> str:
    normalized = normalize_taxonomy_name(value)
    if not normalized:
        return ""
    if "hybrid" in normalized:
        return "Hybrid"
    if "remote" in normalized or "work from home" in normalized or "home office" in normalized:
        return "Remote"
    if any(token in normalized for token in ("on-site", "onsite", "on site", "office")):
        return "On-site"
    return normalize_text(value)


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


def _merge_evidence(*groups: Iterable[str]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        merged.extend(group)
    return normalize_and_dedupe_texts(merged)


def compute_source_text_hash(profile_text: str) -> str:
    return hashlib.sha256(profile_text.encode("utf-8")).hexdigest()


def compute_candidate_id(
    profile_text: str,
    candidate_id: str | None = None,
) -> str:
    if candidate_id is not None:
        normalized = normalize_text(candidate_id)
        if not normalized:
            raise ValueError("candidate_id must not be empty")
        return normalized

    return f"candidate_{compute_source_text_hash(profile_text)[:12]}"


class CandidateProfileEvidenceBackedItem(BaseModel):
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
        return normalize_and_dedupe_texts(values)


class CandidateProfileFeatureItem(CandidateProfileEvidenceBackedItem):
    name: str
    strength: Literal["core", "strong", "secondary", "exposure"]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_item(self) -> "CandidateProfileFeatureItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for extracted feature items")
        return self


class CandidateProfileLanguageItem(CandidateProfileEvidenceBackedItem):
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
        normalized = normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @field_validator("level", mode="before")
    @classmethod
    def clean_level(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = normalize_taxonomy_name(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_item(self) -> "CandidateProfileLanguageItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for extracted language items")
        return self


class CandidateProfileSeniorityItem(CandidateProfileEvidenceBackedItem):
    value: Optional[Literal["junior", "medior", "senior", "lead", "principal", "staff"]]

    @field_validator("value", mode="before")
    @classmethod
    def clean_value(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = normalize_taxonomy_name(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_item(self) -> "CandidateProfileSeniorityItem":
        if self.value is not None and not self.evidence:
            raise ValueError("evidence must not be empty when seniority has a value")
        return self


class CandidateProfileYearsExperienceItem(CandidateProfileEvidenceBackedItem):
    value: Optional[int]

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("years_experience_total.value must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_item(self) -> "CandidateProfileYearsExperienceItem":
        if self.value is not None and not self.evidence:
            raise ValueError(
                "evidence must not be empty when years_experience_total has a value"
            )
        return self


class CandidateProfileCandidateConstraints(CandidateProfileEvidenceBackedItem):
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
        "notes",
        mode="after",
    )
    @classmethod
    def clean_list_fields(cls, values: List[str]) -> List[str]:
        return normalize_and_dedupe_texts(values)

    @field_validator(
        "preferred_workplace_types",
        "excluded_workplace_types",
        mode="after",
    )
    @classmethod
    def clean_workplace_types(cls, values: List[str]) -> List[str]:
        cleaned_values = [
            _normalize_workplace_type(value)
            for value in values
            if _normalize_workplace_type(value)
        ]
        return normalize_and_dedupe_texts(cleaned_values)

    @model_validator(mode="after")
    def validate_item(self) -> "CandidateProfileCandidateConstraints":
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


class CandidateProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[CandidateProfileFeatureItem]
    languages: List[CandidateProfileLanguageItem]
    protocols: List[CandidateProfileFeatureItem]
    standards: List[CandidateProfileFeatureItem]
    domains: List[CandidateProfileFeatureItem]
    seniority: CandidateProfileSeniorityItem
    years_experience_total: CandidateProfileYearsExperienceItem
    candidate_constraints: CandidateProfileCandidateConstraints

    @field_validator("skills", "protocols", "standards", "domains", mode="after")
    @classmethod
    def dedupe_feature_items(
        cls,
        values: List[CandidateProfileFeatureItem],
    ) -> List[CandidateProfileFeatureItem]:
        deduped: dict[str, CandidateProfileFeatureItem] = {}

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
            deduped[value.name] = CandidateProfileFeatureItem(
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
        values: List[CandidateProfileLanguageItem],
    ) -> List[CandidateProfileLanguageItem]:
        deduped: dict[str, CandidateProfileLanguageItem] = {}

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

            deduped[value.name] = CandidateProfileLanguageItem(
                name=existing.name,
                level=preferred_level,
                confidence=max(existing.confidence, value.confidence),
                evidence=_merge_evidence(existing.evidence, value.evidence),
            )

        return list(deduped.values())


class CandidateProfileDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    source_text_hash: str
    schema_version: str
    profile: CandidateProfilePayload

    @field_validator("candidate_id", mode="before")
    @classmethod
    def validate_candidate_id(cls, value: Any) -> str:
        normalized = normalize_text(str(value or ""))
        if not normalized:
            raise ValueError("candidate_id must not be empty")
        return normalized

    @field_validator("source_text_hash")
    @classmethod
    def validate_source_text_hash(cls, value: str) -> str:
        normalized = normalize_text(value)
        if len(normalized) != 64:
            raise ValueError("source_text_hash must be a sha256 hex digest")
        return normalized

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        normalized = normalize_text(value)
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
def _load_candidate_profile_schema() -> Dict[str, Any]:
    return load_json_file(SCHEMA_PATH)


def _render_llm_output_schema_json() -> str:
    root_schema = _load_candidate_profile_schema()
    profile_schema = root_schema["$defs"]["candidateProfile"]
    return render_json(build_json_schema_example(profile_schema, root_schema))


def _render_candidate_context_json(candidate_context: Any) -> str:
    return render_json(candidate_context)


def render_candidate_profile_user_message(
    profile_text: str,
    *,
    candidate_context: Any | None = None,
) -> str:
    template = _load_user_template()
    return render_template(
        template,
        {
            "{{candidate_profile_schema_json}}": _render_llm_output_schema_json(),
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
    return render_candidate_profile_user_message(
        payload["profile_text"],
        candidate_context=payload.get("candidate_context"),
    )


class CandidateProfileExtractor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = DEFAULT_CANDIDATE_PROFILE_LLM_MODEL,
        timeout_seconds: float = 60.0,
        max_completion_tokens: int = DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=CandidateProfilePayload,
            system_message=_load_system_message(),
            render_user_message=_render_user_message,
            operation_name="Candidate profile extraction",
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
        )

    @classmethod
    def from_env(cls) -> "CandidateProfileExtractor":
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Candidate profile extraction",
        )
        model = os.environ.get(
            "CANDIDATE_PROFILE_LLM_MODEL",
            os.environ.get(
                "SEARCH_PROFILE_LLM_MODEL",
                DEFAULT_CANDIDATE_PROFILE_LLM_MODEL,
            ),
        )
        max_completion_tokens = int(
            os.environ.get(
                "CANDIDATE_PROFILE_LLM_MAX_COMPLETION_TOKENS",
                os.environ.get(
                    "SEARCH_PROFILE_LLM_MAX_COMPLETION_TOKENS",
                    str(DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS),
                ),
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
        candidate_id: str | None = None,
        candidate_context: Any | None = None,
    ) -> CandidateProfileDocument:
        profile = self._extractor.extract(
            _build_extraction_payload(
                profile_text,
                candidate_context=candidate_context,
            )
        )
        return CandidateProfileDocument(
            candidate_id=compute_candidate_id(
                profile_text,
                candidate_id=candidate_id,
            ),
            source_text_hash=compute_source_text_hash(profile_text),
            schema_version=CANDIDATE_PROFILE_SCHEMA_VERSION,
            profile=profile,
        )


@lru_cache(maxsize=1)
def get_default_candidate_profile_extractor() -> CandidateProfileExtractor:
    return CandidateProfileExtractor.from_env()


def extract_profile(
    profile_text: str,
    *,
    candidate_id: str | None = None,
    candidate_context: Any | None = None,
    extractor: CandidateProfileExtractor | None = None,
) -> CandidateProfileDocument:
    active_extractor = extractor or get_default_candidate_profile_extractor()
    return active_extractor.extract(
        profile_text,
        candidate_id=candidate_id,
        candidate_context=candidate_context,
    )


_load_search_profile_schema = _load_candidate_profile_schema
render_search_profile_user_message = render_candidate_profile_user_message

SearchProfileEvidenceBackedItem = CandidateProfileEvidenceBackedItem
SearchProfileFeatureItem = CandidateProfileFeatureItem
SearchProfileLanguageItem = CandidateProfileLanguageItem
SearchProfileSeniorityItem = CandidateProfileSeniorityItem
SearchProfileYearsExperienceItem = CandidateProfileYearsExperienceItem
SearchProfileCandidateConstraints = CandidateProfileCandidateConstraints
SearchProfilePayload = CandidateProfilePayload
SearchProfileDocument = CandidateProfileDocument
SearchProfileExtractor = CandidateProfileExtractor
get_default_search_profile_extractor = get_default_candidate_profile_extractor


__all__ = [
    "DEFAULT_CANDIDATE_PROFILE_LLM_MODEL",
    "DEFAULT_CANDIDATE_PROFILE_MAX_COMPLETION_TOKENS",
    "CANDIDATE_PROFILE_SCHEMA_VERSION",
    "DEFAULT_SEARCH_PROFILE_LLM_MODEL",
    "DEFAULT_SEARCH_PROFILE_MAX_COMPLETION_TOKENS",
    "SEARCH_PROFILE_SCHEMA_VERSION",
    "CandidateProfileFeatureItem",
    "CandidateProfileLanguageItem",
    "CandidateProfileSeniorityItem",
    "CandidateProfileYearsExperienceItem",
    "CandidateProfileCandidateConstraints",
    "CandidateProfilePayload",
    "CandidateProfileDocument",
    "CandidateProfileExtractor",
    "SearchProfileFeatureItem",
    "SearchProfileLanguageItem",
    "SearchProfileSeniorityItem",
    "SearchProfileYearsExperienceItem",
    "SearchProfileCandidateConstraints",
    "SearchProfilePayload",
    "SearchProfileDocument",
    "SearchProfileExtractor",
    "compute_candidate_id",
    "compute_source_text_hash",
    "extract_profile",
    "get_default_candidate_profile_extractor",
    "get_default_search_profile_extractor",
    "render_candidate_profile_user_message",
    "render_search_profile_user_message",
]
