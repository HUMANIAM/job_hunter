from __future__ import annotations

from types import SimpleNamespace

import clients.profiling as profiler_module
from clients.profiling.vacancy_profile_model import VacancyProfile


def test_vacancy_profile_system_message_composes_common_rules() -> None:
    system_message = profiler_module._load_system_message()

    assert "{{COMMON_EXTRACTION_RULES}}" not in system_message
    assert "Every extracted field must be supported by evidence" in system_message
    assert "Confidence must be grounded in the quality of the evidence" in system_message
    assert "### role_titles" in system_message
    assert "Return JSON only." in system_message


def test_vacancy_profile_user_message_includes_cleaned_text() -> None:
    rendered = profiler_module._render_user_message("h1: Mechatronics Technician")

    assert "{{SOURCE_TEXT}}" not in rendered
    assert "h1: Mechatronics Technician" in rendered
    assert "primary should be the single best professional role" in rendered


def test_vacancy_profiler_returns_structured_profile() -> None:
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
    profiler = profiler_module._VacancyProfiler(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
        max_completion_tokens=321,
    )

    profile = profiler.profile("h1: Mechatronics Technician")

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
                    "content": profiler_module._load_system_message(),
                },
                {
                    "role": "user",
                    "content": profiler_module._render_user_message(
                        "h1: Mechatronics Technician"
                    ),
                },
            ],
            "timeout": 9.0,
        }
    ]


def test_vacancy_profiler_defaults_target_mini_model() -> None:
    assert profiler_module._DEFAULT_VACANCY_PROFILE_LLM_MODEL == "gpt-5.4-mini"
    assert profiler_module._DEFAULT_VACANCY_PROFILE_MAX_COMPLETION_TOKENS == 1200


def test_vacancy_profiler_exports_only_external_entrypoint() -> None:
    assert profiler_module.__all__ == ["profile_vacancy_text"]
