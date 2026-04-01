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

DEFAULT_SEARCH_PROFILE_LLM_MODEL = "gpt-4.1-mini"
SEARCH_PROFILE_SCHEMA_VERSION = "1.0.0"

SCHEMA_PATH = Path(__file__).with_name("search_profile_schema.json")
SYSTEM_MESSAGE_PATH = Path(__file__).with_name("search_profile_system_message.md")
USER_TEMPLATE_PATH = Path(__file__).with_name("search_profile_user_message_template.md")


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


def compute_source_text_hash(profile_text: str) -> str:
    return hashlib.sha256(profile_text.encode("utf-8")).hexdigest()


class SearchProfileNamedStrengthItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    strength: Literal["core", "strong", "secondary", "exposure"]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = _normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class SearchProfileLanguageItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class SearchProfileCandidateConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

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


class SearchProfileEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[str]
    languages: List[str]
    protocols: List[str]
    standards: List[str]
    domains: List[str]
    seniority_hint: List[str]
    years_experience_total: List[str]
    candidate_constraints: List[str]

    @field_validator("*", mode="after")
    @classmethod
    def clean_evidence_lists(cls, values: List[str]) -> List[str]:
        return _dedupe_and_strip(values)


class SearchProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[SearchProfileNamedStrengthItem]
    languages: List[SearchProfileLanguageItem]
    protocols: List[SearchProfileNamedStrengthItem]
    standards: List[SearchProfileNamedStrengthItem]
    domains: List[SearchProfileNamedStrengthItem]
    seniority_hint: Optional[
        Literal["junior", "medior", "senior", "lead", "principal", "staff"]
    ]
    years_experience_total: Optional[int]
    candidate_constraints: SearchProfileCandidateConstraints
    evidence: SearchProfileEvidence

    @field_validator("seniority_hint", mode="before")
    @classmethod
    def clean_seniority_hint(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = _normalize_taxonomy_name(value)
        return normalized or None

    @field_validator("years_experience_total")
    @classmethod
    def validate_years_experience_total(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("years_experience_total must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_evidence_alignment(self) -> "SearchProfilePayload":
        if self.skills and not self.evidence.skills:
            raise ValueError("missing evidence for 'skills'")
        if self.languages and not self.evidence.languages:
            raise ValueError("missing evidence for 'languages'")
        if self.protocols and not self.evidence.protocols:
            raise ValueError("missing evidence for 'protocols'")
        if self.standards and not self.evidence.standards:
            raise ValueError("missing evidence for 'standards'")
        if self.domains and not self.evidence.domains:
            raise ValueError("missing evidence for 'domains'")
        if self.seniority_hint is not None and not self.evidence.seniority_hint:
            raise ValueError("missing evidence for 'seniority_hint'")
        if (
            self.years_experience_total is not None
            and not self.evidence.years_experience_total
        ):
            raise ValueError("missing evidence for 'years_experience_total'")

        constraints = self.candidate_constraints
        has_constraints = any(
            (
                constraints.preferred_locations,
                constraints.excluded_locations,
                constraints.preferred_workplace_types,
                constraints.excluded_workplace_types,
                constraints.requires_visa_sponsorship is not None,
                constraints.avoid_export_control_roles is not None,
                constraints.notes,
            )
        )
        if has_constraints and not self.evidence.candidate_constraints:
            raise ValueError("missing evidence for 'candidate_constraints'")

        return self


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
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=SearchProfilePayload,
            system_message=_load_system_message(),
            render_user_message=_render_user_message,
            operation_name="Search profile extraction",
            timeout_seconds=timeout_seconds,
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
        return cls(
            client=OpenAI(api_key=api_key),
            model=model,
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
    "SEARCH_PROFILE_SCHEMA_VERSION",
    "SearchProfileNamedStrengthItem",
    "SearchProfileLanguageItem",
    "SearchProfileCandidateConstraints",
    "SearchProfileEvidence",
    "SearchProfilePayload",
    "SearchProfileDocument",
    "SearchProfileExtractor",
    "compute_source_text_hash",
    "extract_profile",
    "get_default_search_profile_extractor",
    "render_search_profile_user_message",
]
