from __future__ import annotations

from types import SimpleNamespace

import clients.job_profiling.profiling.profiling as vacancy_profiler_module
import clients.profiling.profiling as shared_profiler_module
from clients.job_profiling.profiling.job_profile_schema import VacancyProfile


def test_profile_extractor_system_message_composes_common_rules() -> None:
    system_message = shared_profiler_module._load_system_message()

    assert "{{COMMON_EXTRACTION_RULES}}" not in system_message
    assert "Every extracted field must be supported by evidence" in system_message
    assert "Confidence must be grounded in the quality of the evidence" in system_message
    assert "### role_titles" in system_message
    assert "Return JSON only." in system_message


def test_extract_profile_returns_structured_profile() -> None:
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=VacancyProfile.model_validate(
                                {
                                    "role_titles": {
                                        "primary": " Mechatronics Technician ",
                                        "alternatives": [
                                            " Prototype Technician ",
                                            " Service Technician ",
                                        ],
                                        "confidence": 0.96,
                                        "evidence": [
                                            "h1: Mechatronics Technician",
                                            (
                                                "h2: As a Mechatronics Technician, "
                                                "you are responsible"
                                            ),
                                        ],
                                    }
                                }
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    profile = shared_profiler_module.extract_profile(
        "h1: Mechatronics Technician",
        profile_model=VacancyProfile,
        profile_llm_user_message="rendered user message",
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
        max_completion_tokens=321,
    )

    assert profile == VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "mechatronics technician",
                "alternatives": [
                    "prototype technician",
                    "service technician",
                ],
                "confidence": 0.96,
                "evidence": [
                    "h1: Mechatronics Technician",
                    "h2: As a Mechatronics Technician, you are responsible",
                ],
            }
        }
    )
    assert calls == [
        {
            "model": "gpt-test",
            "n": 1,
            "temperature": 0.0,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "max_completion_tokens": 321,
            "store": False,
            "response_format": VacancyProfile,
            "messages": [
                {
                    "role": "system",
                    "content": shared_profiler_module._load_system_message(),
                },
                {
                    "role": "user",
                    "content": "rendered user message",
                },
            ],
            "timeout": 9.0,
        }
    ]


def test_extract_profile_uses_shared_openai_client_helper(monkeypatch) -> None:
    expected_client = object()
    captured_contexts: list[str] = []

    class FakeExtractor:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["client"] is expected_client
            self._response_format = kwargs["response_format"]

        def extract(self, _: object) -> VacancyProfile:
            return self._response_format.model_validate(
                {
                    "role_titles": {
                        "primary": "mechatronics technician",
                        "alternatives": [],
                        "confidence": 0.96,
                        "evidence": ["h1: Mechatronics Technician"],
                    }
                }
            )

    def fake_get_openai_client(*, error_context: str) -> object:
        captured_contexts.append(error_context)
        return expected_client

    monkeypatch.setattr(
        shared_profiler_module,
        "get_openai_client",
        fake_get_openai_client,
    )
    monkeypatch.setattr(
        shared_profiler_module,
        "OpenAIStructuredExtractor",
        FakeExtractor,
    )

    profile = shared_profiler_module.extract_profile(
        "h1: Mechatronics Technician",
        profile_model=VacancyProfile,
        profile_llm_user_message="rendered user message",
    )

    assert profile.role_titles.primary == "mechatronics technician"
    assert captured_contexts == ["Profile extraction"]


def test_profile_vacancy_text_delegates_to_shared_extractor(monkeypatch) -> None:
    extracted_messages: list[dict[str, object]] = []
    expected_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "mechatronics technician",
                "alternatives": [],
                "confidence": 0.96,
                "evidence": ["h1: Mechatronics Technician"],
            }
        }
    )

    def fake_extract_profile(
        source_text: str,
        *,
        profile_model: type[object],
        profile_llm_user_message: str,
    ) -> VacancyProfile:
        extracted_messages.append(
            {
                "source_text": source_text,
                "profile_model": profile_model,
                "profile_llm_user_message": profile_llm_user_message,
            }
        )
        return expected_profile

    monkeypatch.setattr(
        vacancy_profiler_module,
        "extract_profile",
        fake_extract_profile,
    )

    profile = vacancy_profiler_module.profile_vacancy_text(
        "h1: Mechatronics Technician"
    )

    assert profile == expected_profile
    assert extracted_messages == [
        {
            "source_text": "h1: Mechatronics Technician",
            "profile_model": VacancyProfile,
            "profile_llm_user_message": (
                vacancy_profiler_module.render_job_profile_user_message(
                    "h1: Mechatronics Technician"
                )
            ),
        }
    ]


def test_profile_extractor_defaults_target_mini_model() -> None:
    assert shared_profiler_module.DEFAULT_PROFILE_LLM_MODEL == "gpt-5.4-mini"
    assert shared_profiler_module.DEFAULT_PROFILE_MAX_COMPLETION_TOKENS == 5000


def test_profile_extractor_exports_only_external_entrypoint() -> None:
    assert shared_profiler_module.__all__ == ["extract_profile"]


def test_vacancy_profiler_exports_only_external_entrypoint() -> None:
    assert vacancy_profiler_module.__all__ == ["profile_vacancy_text"]
