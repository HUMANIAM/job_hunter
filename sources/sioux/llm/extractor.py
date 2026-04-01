from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, List, Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

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
    return SYSTEM_MESSAGE_PATH.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_user_template() -> str:
    return USER_TEMPLATE_PATH.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _load_jobs_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _decode_json_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def _resolve_schema_node(
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
) -> dict[str, Any]:
    if "$ref" not in schema_node:
        return schema_node

    ref = schema_node["$ref"]
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref: {ref}")

    resolved_node: Any = root_schema
    for token in ref[2:].split("/"):
        resolved_node = resolved_node[_decode_json_pointer_token(token)]

    resolved_schema = _resolve_schema_node(resolved_node, root_schema)
    if len(schema_node) == 1:
        return resolved_schema

    merged_schema = dict(resolved_schema)
    merged_schema.update({key: value for key, value in schema_node.items() if key != "$ref"})
    return merged_schema


def _render_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _build_prompt_example_from_schema(
    schema_node: dict[str, Any],
    root_schema: dict[str, Any],
) -> Any:
    resolved_schema = _resolve_schema_node(schema_node, root_schema)
    if "enum" in resolved_schema:
        return " | ".join(
            "null" if value is None else str(value)
            for value in resolved_schema["enum"]
        )

    schema_type = resolved_schema.get("type")
    if schema_type == "object":
        return {
            key: _build_prompt_example_from_schema(value, root_schema)
            for key, value in resolved_schema.get("properties", {}).items()
        }

    if schema_type == "array":
        return [_build_prompt_example_from_schema(resolved_schema["items"], root_schema)]

    if schema_type == "string":
        return "string"
    if schema_type == "integer":
        return 0
    if schema_type == "boolean":
        return False

    if isinstance(schema_type, list) and "null" in schema_type:
        return None

    raise ValueError(f"unsupported schema node for prompt example: {resolved_schema}")


def _render_llm_output_schema_json() -> str:
    root_schema = _load_jobs_schema()
    llm_schema = root_schema["$defs"]["llmExtraction"]
    return _render_json(_build_prompt_example_from_schema(llm_schema, root_schema))


def _render_deterministic_fields_json(job: Any) -> str:
    root_schema = _load_jobs_schema()
    deterministic_schema = _resolve_schema_node(
        root_schema["$defs"]["siouxJobDeterministicContext"],
        root_schema,
    )
    deterministic_context = {
        field_name: getattr(job, field_name)
        for field_name in deterministic_schema["properties"]
    }
    return _render_json(deterministic_context)


def render_llm_user_message(job: Any) -> str:
    template = _load_user_template()
    rendered_placeholders = {
        "{{llm_output_schema_json}}": _render_llm_output_schema_json(),
        "{{deterministic_fields_json}}": _render_deterministic_fields_json(job),
        "{{description_text}}": getattr(job, "description_text").replace("```", "'''"),
    }

    for placeholder, value in rendered_placeholders.items():
        template = template.replace(placeholder, value)

    return template


class SiouxLlmExtractor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = DEFAULT_SIOUX_LLM_MODEL,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._client = client
        self._model = model
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "SiouxLlmExtractor":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for Sioux LLM extraction")

        model = os.environ.get("SIOUX_LLM_MODEL", DEFAULT_SIOUX_LLM_MODEL)
        return cls(
            client=OpenAI(api_key=api_key),
            model=model,
        )

    def extract(self, job: Any) -> SiouxLlmExtractionPayload:
        completion = self._client.chat.completions.parse(
            model=self._model,
            temperature=0,
            max_completion_tokens=1400,
            store=False,
            response_format=SiouxLlmExtractionPayload,
            messages=[
                {"role": "system", "content": _load_system_message()},
                {"role": "user", "content": render_llm_user_message(job)},
            ],
            timeout=self._timeout_seconds,
        )

        message = completion.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise RuntimeError(f"Sioux LLM extraction refused the request: {refusal}")

        if message.parsed is None:
            raise RuntimeError("Sioux LLM extraction did not return parsed JSON output")

        return message.parsed


@lru_cache(maxsize=1)
def get_default_llm_extractor() -> SiouxLlmExtractor:
    return SiouxLlmExtractor.from_env()
