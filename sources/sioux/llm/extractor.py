from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, List, Literal, Optional

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
    resolve_json_schema_node,
)
from shared.normalizer import (
    normalize_and_dedupe_texts,
    normalize_taxonomy_name,
    normalize_text,
)

DEFAULT_SIOUX_LLM_MODEL = "gpt-4.1-mini"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "jobs_sioux.schema.json"
SYSTEM_MESSAGE_PATH = Path(__file__).with_name("system_message.md")
USER_TEMPLATE_PATH = Path(__file__).with_name("user_message_template.md")

FEATURE_COLLECTION_FIELDS = (
    "skills",
    "languages",
    "protocols",
    "standards",
    "domains",
)
REQUIREMENT_LEVEL_RANK = {
    "preferred": 0,
    "required": 1,
}

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


class SiouxLlmEvidenceBackedItem(BaseModel):
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


class SiouxLlmFeatureItem(SiouxLlmEvidenceBackedItem):
    name: str
    requirement_level: Literal["required", "preferred"]

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized

    @field_validator("requirement_level", mode="before")
    @classmethod
    def clean_requirement_level(cls, value: str) -> str:
        normalized = normalize_taxonomy_name(value)
        if normalized not in REQUIREMENT_LEVEL_RANK:
            raise ValueError("requirement_level must be 'required' or 'preferred'")
        return normalized

    @model_validator(mode="after")
    def validate_item(self) -> "SiouxLlmFeatureItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for extracted feature items")
        return self


class SiouxLlmRestrictionItem(SiouxLlmEvidenceBackedItem):
    value: str

    @field_validator("value", mode="before")
    @classmethod
    def clean_value(cls, value: str) -> str:
        normalized = normalize_taxonomy_name(value)
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_item(self) -> "SiouxLlmRestrictionItem":
        if not self.evidence:
            raise ValueError("evidence must not be empty for restrictions")
        return self


class SiouxLlmSeniorityItem(SiouxLlmEvidenceBackedItem):
    value: Optional[Literal["junior", "medior", "senior", "lead", "principal", "staff"]]

    @field_validator("value", mode="before")
    @classmethod
    def clean_value(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = normalize_taxonomy_name(value)
        return normalized or None

    @model_validator(mode="after")
    def validate_item(self) -> "SiouxLlmSeniorityItem":
        if self.value is not None and not self.evidence:
            raise ValueError("evidence must not be empty when seniority has a value")
        return self


def _merge_feature_items(
    values: List[SiouxLlmFeatureItem],
) -> List[SiouxLlmFeatureItem]:
    merged_values: dict[str, SiouxLlmFeatureItem] = {}

    for value in values:
        existing = merged_values.get(value.name)
        if existing is None:
            merged_values[value.name] = value
            continue

        best_requirement_level = (
            value.requirement_level
            if REQUIREMENT_LEVEL_RANK[value.requirement_level]
            > REQUIREMENT_LEVEL_RANK[existing.requirement_level]
            else existing.requirement_level
        )
        merged_values[value.name] = SiouxLlmFeatureItem(
            name=value.name,
            requirement_level=best_requirement_level,
            confidence=max(existing.confidence, value.confidence),
            evidence=_merge_evidence(existing.evidence, value.evidence),
        )

    return list(merged_values.values())


def _merge_restriction_items(
    values: List[SiouxLlmRestrictionItem],
) -> List[SiouxLlmRestrictionItem]:
    merged_values: dict[str, SiouxLlmRestrictionItem] = {}

    for value in values:
        existing = merged_values.get(value.value)
        if existing is None:
            merged_values[value.value] = value
            continue

        merged_values[value.value] = SiouxLlmRestrictionItem(
            value=value.value,
            confidence=max(existing.confidence, value.confidence),
            evidence=_merge_evidence(existing.evidence, value.evidence),
        )

    return list(merged_values.values())


class SiouxLlmExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: List[SiouxLlmFeatureItem]
    languages: List[SiouxLlmFeatureItem]
    protocols: List[SiouxLlmFeatureItem]
    standards: List[SiouxLlmFeatureItem]
    domains: List[SiouxLlmFeatureItem]
    seniority: SiouxLlmSeniorityItem
    restrictions: List[SiouxLlmRestrictionItem]

    @field_validator(*FEATURE_COLLECTION_FIELDS, mode="after")
    @classmethod
    def merge_feature_lists(
        cls,
        values: List[SiouxLlmFeatureItem],
    ) -> List[SiouxLlmFeatureItem]:
        return _merge_feature_items(values)

    @field_validator("restrictions", mode="after")
    @classmethod
    def merge_restrictions(
        cls,
        values: List[SiouxLlmRestrictionItem],
    ) -> List[SiouxLlmRestrictionItem]:
        return _merge_restriction_items(values)


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return load_text_file(SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_user_template() -> str:
    return load_text_file(USER_TEMPLATE_PATH)


@lru_cache(maxsize=1)
def _load_jobs_schema() -> dict[str, Any]:
    return load_json_file(SCHEMA_PATH)


def _render_llm_output_schema_json() -> str:
    root_schema = _load_jobs_schema()
    llm_schema = root_schema["$defs"]["llmExtraction"]
    return render_json(build_json_schema_example(llm_schema, root_schema))


def _render_deterministic_fields_json(job: Any) -> str:
    root_schema = _load_jobs_schema()
    deterministic_schema = resolve_json_schema_node(
        root_schema["$defs"]["siouxJobDeterministicContext"],
        root_schema,
    )
    deterministic_context = {
        field_name: getattr(job, field_name)
        for field_name in deterministic_schema["properties"]
    }
    return render_json(deterministic_context)


def render_llm_user_message(job: Any) -> str:
    template = _load_user_template()
    return render_template(
        template,
        {
            "{{llm_output_schema_json}}": _render_llm_output_schema_json(),
            "{{deterministic_fields_json}}": _render_deterministic_fields_json(job),
            "{{description_text}}": getattr(job, "description_text").replace(
                "```", "'''"
            ),
        },
    )


class SiouxLlmExtractor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = DEFAULT_SIOUX_LLM_MODEL,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=SiouxLlmExtractionPayload,
            system_message=_load_system_message(),
            render_user_message=render_llm_user_message,
            operation_name="Sioux LLM extraction",
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_env(cls) -> "SiouxLlmExtractor":
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Sioux LLM extraction",
        )
        model = os.environ.get("SIOUX_LLM_MODEL", DEFAULT_SIOUX_LLM_MODEL)
        return cls(
            client=OpenAI(api_key=api_key),
            model=model,
        )

    def extract(self, job: Any) -> SiouxLlmExtractionPayload:
        return self._extractor.extract(job)


@lru_cache(maxsize=1)
def get_default_llm_extractor() -> SiouxLlmExtractor:
    return SiouxLlmExtractor.from_env()
