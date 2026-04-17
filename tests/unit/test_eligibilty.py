from __future__ import annotations

from types import SimpleNamespace

from clients.candidate_profiling.candidate_profile_schema import CandidateProfile
from clients.eligibility import eligibilty as eligibilty_module
from clients.eligibility.eligibility_response_model import EligibilityResponse
from clients.job_profiling.profiling.job_profile_model import VacancyProfile


def test_render_eligibilty_user_message_uses_input_view_maps(monkeypatch) -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "candidate role",
                "confidence": 0.94,
                "evidence": ["candidate evidence"],
            }
        }
    )
    vacancy_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "job role",
                "confidence": 0.9,
                "evidence": ["job evidence"],
            }
        }
    )

    monkeypatch.setattr(
        eligibilty_module.EligibilityInputView,
        "get_candidate_view",
        lambda _candidate_profile: {
            "{{CANDIDATE_ROLE_PRIMARY}}": "candidate from view",
        },
    )
    monkeypatch.setattr(
        eligibilty_module.EligibilityInputView,
        "get_job_view",
        lambda _vacancy_profile: {
            "{{VACANCY_ROLE_PRIMARY}}": "job from view",
        },
    )

    rendered = eligibilty_module.render_eligibilty_user_message(
        candidate_profile,
        vacancy_profile,
    )

    assert "candidate from view" in rendered
    assert "job from view" in rendered


def test_render_eligibilty_user_message_uses_candidate_placeholder_values() -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "alternatives": ["firmware engineer"],
                "confidence": 0.94,
                "evidence": ["CV headline: Embedded Software Engineer"],
            },
            "education": {
                "min_level": "bachelor",
                "accepted_fields": ["electrical engineering"],
                "confidence": 0.8,
                "evidence": ["BSc Electrical Engineering"],
            },
            "experience": {
                "min_years": 7,
                "seniority_band": "senior",
                "confidence": 0.88,
                "evidence": ["7 years embedded systems experience"],
            },
            "languages": [
                {
                    "name": "english",
                    "strength": "strong",
                    "confidence": 0.9,
                    "evidence": ["Daily work language"],
                }
            ],
            "technical_experience": {
                "technical_core_features": [
                    {
                        "name": "embedded c",
                        "strength": "core",
                        "confidence": 0.95,
                        "evidence": ["Built production firmware in C"],
                    }
                ],
                "technologies": [
                    {
                        "name": "python",
                        "strength": "secondary",
                        "confidence": 0.7,
                        "evidence": ["Test automation tooling"],
                    }
                ],
            },
        }
    )
    vacancy_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software designer",
                "alternatives": ["embedded engineer"],
                "confidence": 0.9,
                "evidence": ["Vacancy title"],
            },
            "education": {
                "min_level": "bachelor",
                "accepted_fields": ["electrical engineering", "computer science"],
                "confidence": 0.8,
                "evidence": ["Vacancy education section"],
            },
            "experience": {
                "min_years": 5,
                "seniority_band": "senior",
                "confidence": 0.85,
                "evidence": ["Vacancy experience section"],
            },
            "languages": {
                "required": ["english"],
                "preferred": ["dutch"],
                "confidence": 0.8,
                "evidence": ["Vacancy language section"],
            },
            "technical_experience_requirements": {
                "technical_core_features": {
                    "required": ["embedded c"],
                    "preferred": ["rtos"],
                    "confidence": 0.9,
                    "evidence": ["Vacancy technical requirements"],
                },
                "technologies": {
                    "required": ["can"],
                    "preferred": ["python"],
                    "confidence": 0.9,
                    "evidence": ["Vacancy technology section"],
                },
            },
        }
    )

    rendered = eligibilty_module.render_eligibilty_user_message(
        candidate_profile,
        vacancy_profile,
    )

    assert "{{CANDIDATE_ROLE_PRIMARY}}" not in rendered
    assert "{{CANDIDATE_TECHNOLOGIES}}" not in rendered
    assert "{{" not in rendered
    assert "embedded software engineer" in rendered
    assert "firmware engineer" in rendered
    assert "english (strong)" in rendered
    assert "- embedded c (core)" in rendered
    assert "- python (secondary)" in rendered
    assert "embedded software designer" in rendered
    assert "- can (required)" in rendered
    assert "- python (preferred)" in rendered


def test_render_eligibilty_user_message_renders_missing_candidate_fields() -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "confidence": 0.94,
                "evidence": ["CV headline: Embedded Software Engineer"],
            }
        }
    )
    vacancy_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software designer",
                "confidence": 0.9,
                "evidence": ["Vacancy title"],
            }
        }
    )

    rendered = eligibilty_module.render_eligibilty_user_message(
        candidate_profile,
        vacancy_profile,
    )

    assert "| Alternatives | none | none |" in rendered
    assert "| minimum level | not specified | not specified |" in rendered
    assert "| required | not specified | not specified |" in rendered
    assert "### Candidate\nnot specified" in rendered


def test_evaluate_eligibility_uses_structured_extractor_with_rendered_prompt() -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "confidence": 0.94,
                "evidence": ["candidate evidence"],
            }
        }
    )
    vacancy_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software designer",
                "confidence": 0.9,
                "evidence": ["vacancy evidence"],
            }
        }
    )
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=EligibilityResponse.model_validate(
                                {
                                    "eligibility_score": 0.72,
                                    "decision": "uncertain",
                                    "blocker_reasons": [],
                                    "support_reasons": ["role titles overlap"],
                                    "field_assessments": [
                                        {
                                            "field": "role_titles",
                                            "decision": "partial",
                                            "confidence": 0.72,
                                            "evidence": ["primary titles are related"],
                                        }
                                    ],
                                }
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    result = eligibilty_module.evaluate_eligibility(
        candidate_profile,
        vacancy_profile,
        client=fake_client,
        model="gpt-test",
        max_completion_tokens=321,
        timeout_seconds=9.0,
    )

    assert result == EligibilityResponse.model_validate(
        {
            "eligibility_score": 0.72,
            "decision": "uncertain",
            "blocker_reasons": [],
            "support_reasons": ["role titles overlap"],
            "field_assessments": [
                {
                    "field": "role_titles",
                    "decision": "partial",
                    "confidence": 0.72,
                    "evidence": ["primary titles are related"],
                }
            ],
        }
    )
    assert calls[0]["model"] == "gpt-test"
    assert calls[0]["response_format"] is EligibilityResponse
    assert calls[0]["max_completion_tokens"] == 321
    assert calls[0]["timeout"] == 9.0
    assert "You evaluate candidate eligibility" in calls[0]["messages"][0]["content"]
    assert "embedded software engineer" in calls[0]["messages"][1]["content"]
    assert "embedded software designer" in calls[0]["messages"][1]["content"]
