from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from clients.candidate_profiling.candidate_profile_model import CandidateProfile
from clients.eligibility.eligibility_input_view import EligibilityInputView
from clients.eligibility.eligibility_response_model import EligibilityResponse
from clients.job_profiling.profiling.job_profile_model import VacancyProfile
from shared.env import require_env_value
from shared.llm import OpenAIStructuredExtractor, load_text_file, render_template

MODULE_DIR = Path(__file__).resolve().parent
ELIGIBILTY_USER_MESSAGE_PATH = MODULE_DIR / "eligibilty_user_message.md"
ELIGIBILTY_SYSTEM_MESSAGE_PATH = MODULE_DIR / "eligibilty_system_message.md"

DEFAULT_ELIGIBILITY_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_ELIGIBILITY_MAX_COMPLETION_TOKENS = 1800
ELIGIBILITY_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True)
class _EligibilityPayload:
    candidate_profile: CandidateProfile
    vacancy_profile: VacancyProfile


@lru_cache(maxsize=1)
def _load_eligibilty_user_message_template() -> str:
    return load_text_file(ELIGIBILTY_USER_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_eligibilty_system_message() -> str:
    return load_text_file(ELIGIBILTY_SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    api_key = require_env_value(
        "OPENAI_API_KEY",
        error_context="Eligibility evaluation",
    )
    return OpenAI(api_key=api_key)


def render_eligibilty_user_message(
    candidate_profile: CandidateProfile,
    vacancy_profile: VacancyProfile,
) -> str:
    return render_template(
        _load_eligibilty_user_message_template(),
        {
            **EligibilityInputView.get_job_view(vacancy_profile),
            **EligibilityInputView.get_candidate_view(candidate_profile),
        },
    )


def _render_eligibility_user_message(payload: _EligibilityPayload) -> str:
    return render_eligibilty_user_message(
        payload.candidate_profile,
        payload.vacancy_profile,
    )


def evaluate_eligibility(
    candidate_profile: CandidateProfile,
    vacancy_profile: VacancyProfile,
    *,
    client: OpenAI | None = None,
    model: str = DEFAULT_ELIGIBILITY_LLM_MODEL,
    max_completion_tokens: int = DEFAULT_ELIGIBILITY_MAX_COMPLETION_TOKENS,
    timeout_seconds: float = ELIGIBILITY_TIMEOUT_SECONDS,
) -> EligibilityResponse:
    extractor = OpenAIStructuredExtractor(
        client=client or _get_openai_client(),
        model=model,
        response_format=EligibilityResponse,
        system_message=_load_eligibilty_system_message(),
        render_user_message=_render_eligibility_user_message,
        operation_name="Eligibility evaluation",
        timeout_seconds=timeout_seconds,
        max_completion_tokens=max_completion_tokens,
    )
    return extractor.extract(
        _EligibilityPayload(
            candidate_profile=candidate_profile,
            vacancy_profile=vacancy_profile,
        )
    )


__all__ = [
    "EligibilityResponse",
    "evaluate_eligibility",
    "render_eligibilty_user_message",
]
