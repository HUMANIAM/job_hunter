from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.env import require_env_value
from shared.llm import (
    OpenAIStructuredExtractor,
    load_text_file,
    render_json,
    render_template,
)
from shared.normalizer import normalize_and_dedupe_texts, normalize_taxonomy_name

DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS = 2000

MODULE_DIR = Path(__file__).resolve().parent
LLM_DIR = MODULE_DIR / "llm"

SYSTEM_MESSAGE_PATH = LLM_DIR / "job_eligibility_view_system_message.md"
USER_TEMPLATE_PATH = LLM_DIR / "job_eligibility_view_user_message_template.md"


def _clean_string_list(values: List[str]) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        normalized = normalize_taxonomy_name(value)
        if normalized:
            cleaned.append(normalized)
    return normalize_and_dedupe_texts(cleaned)


class SetFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)

    @field_validator("allowed", "excluded", mode="after")
    @classmethod
    def clean_values(cls, values: List[str]) -> List[str]:
        return _clean_string_list(values)


class JobEligibilityViewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_families: Optional[SetFilter] = None
    locations: Optional[SetFilter] = None
    workplace_types: Optional[SetFilter] = None
    languages: Optional[SetFilter] = None
    seniority_levels: Optional[SetFilter] = None
    job_conditions: Optional[SetFilter] = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "JobEligibilityViewPayload":
        if not any(
            (
                self.role_families,
                self.locations,
                self.workplace_types,
                self.languages,
                self.seniority_levels,
                self.job_conditions,
            )
        ):
            raise ValueError("job eligibility view must contain at least one constrained aspect")
        return self


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return load_text_file(SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_user_template() -> str:
    return load_text_file(USER_TEMPLATE_PATH)


def render_job_eligibility_view_user_message(job_profile: Any) -> str:
    template = _load_user_template()
    rendered_job_profile = render_json(job_profile)
    return render_template(
        template,
        {
            "{{JOB_PROFILE}}": rendered_job_profile,
        },
    )


def _build_extraction_payload(job_profile: Any) -> Dict[str, Any]:
    return {
        "job_profile": job_profile,
    }


def _render_user_message(payload: Dict[str, Any]) -> str:
    return render_job_eligibility_view_user_message(payload["job_profile"])


class JobEligibilityViewExtractor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL,
        timeout_seconds: float = 60.0,
        max_completion_tokens: int = DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=JobEligibilityViewPayload,
            system_message=_load_system_message(),
            render_user_message=_render_user_message,
            operation_name="Job eligibility view extraction",
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
        )

    @classmethod
    def from_env(cls) -> "JobEligibilityViewExtractor":
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Job eligibility view extraction",
        )
        model = os.environ.get(
            "JOB_ELIGIBILITY_VIEW_LLM_MODEL",
            DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL,
        )
        max_completion_tokens = int(
            os.environ.get(
                "JOB_ELIGIBILITY_VIEW_LLM_MAX_COMPLETION_TOKENS",
                str(DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS),
            )
        )
        return cls(
            client=OpenAI(api_key=api_key),
            model=model,
            max_completion_tokens=max_completion_tokens,
        )

    def extract(self, job_profile: Any) -> JobEligibilityViewPayload:
        return self._extractor.extract(_build_extraction_payload(job_profile))


@lru_cache(maxsize=1)
def get_default_job_eligibility_view_extractor() -> JobEligibilityViewExtractor:
    return JobEligibilityViewExtractor.from_env()


def extract_job_eligibility_view(
    job_profile: Any,
    *,
    extractor: JobEligibilityViewExtractor | None = None,
) -> JobEligibilityViewPayload:
    active_extractor = extractor or get_default_job_eligibility_view_extractor()
    return active_extractor.extract(job_profile)


__all__ = [
    "DEFAULT_JOB_ELIGIBILITY_VIEW_LLM_MODEL",
    "DEFAULT_JOB_ELIGIBILITY_VIEW_MAX_COMPLETION_TOKENS",
    "SetFilter",
    "JobEligibilityViewPayload",
    "JobEligibilityViewExtractor",
    "extract_job_eligibility_view",
    "get_default_job_eligibility_view_extractor",
    "render_job_eligibility_view_user_message",
]
