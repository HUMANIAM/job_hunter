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

DEFAULT_SIOUX_LLM_MODEL = "gpt-4.1-mini"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "jobs_sioux.schema.json"
SYSTEM_MESSAGE_PATH = Path(__file__).with_name("system_message.md")
USER_TEMPLATE_PATH = Path(__file__).with_name("user_message_template.md")

ARRAY_EXTRACTION_FIELDS = (
    "required_skills",
    "preferred_skills",
    "required_languages",
    "preferred_languages",
    "required_protocols",
    "preferred_protocols",
    "required_standards",
    "preferred_standards",
    "required_domains",
    "preferred_domains",
    "restrictions",
)


def _dedupe_and_strip(values: Iterable[str]) -> List[str]:
    cleaned_values: List[str] = []
    seen_values: set[str] = set()

    for value in values:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen_values:
            continue
        cleaned_values.append(normalized)
        seen_values.add(key)

    return cleaned_values


class SiouxLlmEvidencePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_skills: List[str]
    preferred_skills: List[str]
    required_languages: List[str]
    preferred_languages: List[str]
    required_protocols: List[str]
    preferred_protocols: List[str]
    required_standards: List[str]
    preferred_standards: List[str]
    required_domains: List[str]
    preferred_domains: List[str]
    seniority_hint: List[str]
    restrictions: List[str]

    @field_validator("*", mode="after")
    @classmethod
    def clean_evidence_lists(cls, values: List[str]) -> List[str]:
        return _dedupe_and_strip(values)


class SiouxLlmExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_skills: List[str]
    preferred_skills: List[str]
    required_languages: List[str]
    preferred_languages: List[str]
    required_protocols: List[str]
    preferred_protocols: List[str]
    required_standards: List[str]
    preferred_standards: List[str]
    required_domains: List[str]
    preferred_domains: List[str]
    seniority_hint: Optional[
        Literal[
        "junior",
        "medior",
        "senior",
        "lead",
        "principal",
        "staff",
        ]
    ]
    restrictions: List[str]
    evidence: SiouxLlmEvidencePayload

    @field_validator(*ARRAY_EXTRACTION_FIELDS, mode="after")
    @classmethod
    def clean_extraction_lists(cls, values: List[str]) -> List[str]:
        return _dedupe_and_strip(values)

    @field_validator("seniority_hint", mode="before")
    @classmethod
    def clean_seniority_hint(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip().lower()
        return normalized or None

    @model_validator(mode="after")
    def validate_evidence_alignment(self) -> "SiouxLlmExtractionPayload":
        for field_name in ARRAY_EXTRACTION_FIELDS[:-1]:
            if getattr(self, field_name) and not getattr(self.evidence, field_name):
                raise ValueError(f"missing evidence for '{field_name}'")

        if self.seniority_hint is not None and not self.evidence.seniority_hint:
            raise ValueError("missing evidence for 'seniority_hint'")

        if self.restrictions and not self.evidence.restrictions:
            raise ValueError("missing evidence for 'restrictions'")

        return self


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
