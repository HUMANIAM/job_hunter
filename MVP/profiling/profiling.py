from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from shared.llm import (
    OpenAIStructuredExtractor,
    get_openai_client,
    load_text_file,
    render_template,
)

ProfileModelT = TypeVar("ProfileModelT", bound=BaseModel)

DEFAULT_PROFILE_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_PROFILE_MAX_COMPLETION_TOKENS = 5000
PROFILE_TIMEOUT_SECONDS = 60.0

MODULE_DIR = Path(__file__).resolve().parent

COMMON_PROFILE_SYSTEM_MESSAGE_PATH = MODULE_DIR / "common_profile_system_message.md"
COMMON_EXTRACTION_RULES_PATH = MODULE_DIR / "common_extraction_rules.md"


@dataclass(frozen=True)
class _ProfileExtractionPayload:
    source_text: str
    profile_llm_user_message: str


@lru_cache(maxsize=1)
def _load_common_profile_system_message_template() -> str:
    return load_text_file(COMMON_PROFILE_SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_common_extraction_rules() -> str:
    return load_text_file(COMMON_EXTRACTION_RULES_PATH)


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return render_template(
        _load_common_profile_system_message_template(),
        {
            "{{COMMON_EXTRACTION_RULES}}": _load_common_extraction_rules(),
        },
    )


def _render_extractor_user_message(payload: _ProfileExtractionPayload) -> str:
    return payload.profile_llm_user_message


def extract_profile(
    source_text: str,
    *,
    profile_model: type[ProfileModelT],
    profile_llm_user_message: str,
    client: OpenAI | None = None,
    model: str = DEFAULT_PROFILE_LLM_MODEL,
    max_completion_tokens: int = DEFAULT_PROFILE_MAX_COMPLETION_TOKENS,
    timeout_seconds: float = PROFILE_TIMEOUT_SECONDS,
) -> ProfileModelT:
    extractor = OpenAIStructuredExtractor(
        client=client or get_openai_client(error_context="Profile extraction"),
        model=model,
        response_format=profile_model,
        system_message=_load_system_message(),
        render_user_message=_render_extractor_user_message,
        operation_name=f"{profile_model.__name__} extraction",
        timeout_seconds=timeout_seconds,
        max_completion_tokens=max_completion_tokens,
    )
    return extractor.extract(
        _ProfileExtractionPayload(
            source_text=source_text,
            profile_llm_user_message=profile_llm_user_message,
        )
    )


__all__ = ["extract_profile"]
