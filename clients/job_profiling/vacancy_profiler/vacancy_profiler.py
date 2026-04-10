from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

from openai import OpenAI

from clients.job_profiling.vacancy_profiler.vacancy_profile_model import VacancyProfile
from shared.env import require_env_value
from shared.llm import OpenAIStructuredExtractor, load_text_file, render_template

_DEFAULT_VACANCY_PROFILE_LLM_MODEL = "gpt-5.4-mini"
_DEFAULT_VACANCY_PROFILE_MAX_COMPLETION_TOKENS = 1200
_VACANCY_PROFILE_TIMEOUT_SECONDS = 60.0

MODULE_DIR = Path(__file__).resolve().parent
COMMON_DIR = MODULE_DIR / "common"

COMMON_PROFILE_SYSTEM_MESSAGE_PATH = COMMON_DIR / "common_profile_system_message.md"
COMMON_EXTRACTION_RULES_PATH = COMMON_DIR / "common_extraction_rules.md"
JOB_PROFILE_USER_MESSAGE_PATH = COMMON_DIR / "job_profile_user_message.md"


@lru_cache(maxsize=1)
def _load_common_profile_system_message_template() -> str:
    return load_text_file(COMMON_PROFILE_SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_common_extraction_rules() -> str:
    return load_text_file(COMMON_EXTRACTION_RULES_PATH)


@lru_cache(maxsize=1)
def _load_job_profile_user_message_template() -> str:
    return load_text_file(JOB_PROFILE_USER_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return render_template(
        _load_common_profile_system_message_template(),
        {
            "{{COMMON_EXTRACTION_RULES}}": _load_common_extraction_rules(),
        },
    )


def _render_user_message(cleaned_vacancy_text: str) -> str:
    return render_template(
        _load_job_profile_user_message_template(),
        {
            "{{SOURCE_TEXT}}": cleaned_vacancy_text.replace("```", "'''"),
        },
    )


def _build_extraction_payload(cleaned_vacancy_text: str) -> Dict[str, str]:
    return {
        "cleaned_vacancy_text": cleaned_vacancy_text,
    }


def _render_extractor_user_message(payload: Dict[str, str]) -> str:
    return _render_user_message(payload["cleaned_vacancy_text"])


class _VacancyProfiler:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = _DEFAULT_VACANCY_PROFILE_LLM_MODEL,
        max_completion_tokens: int = _DEFAULT_VACANCY_PROFILE_MAX_COMPLETION_TOKENS,
        timeout_seconds: float = _VACANCY_PROFILE_TIMEOUT_SECONDS,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=VacancyProfile,
            system_message=_load_system_message(),
            render_user_message=_render_extractor_user_message,
            operation_name="Vacancy profile extraction",
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
        )

    @classmethod
    def create(cls) -> "_VacancyProfiler":
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Vacancy profile extraction",
        )
        return cls(
            client=OpenAI(api_key=api_key),
        )

    def profile(self, cleaned_vacancy_text: str) -> VacancyProfile:
        return self._extractor.extract(
            _build_extraction_payload(cleaned_vacancy_text)
        )


@lru_cache(maxsize=1)
def _get_vacancy_profiler() -> _VacancyProfiler:
    return _VacancyProfiler.create()


def profile_vacancy_text(cleaned_vacancy_text: str) -> VacancyProfile:
    profiler = _get_vacancy_profiler()
    return profiler.profile(cleaned_vacancy_text)


__all__ = [
    "profile_vacancy_text",
]
