from __future__ import annotations

from clients.candidate_profiling.candidate_profile_model import CandidateProfile
from clients.eligibility.eligibility_input_view import EligibilityInputView
from clients.job_profiling.profiling.job_profile_model import VacancyProfile


def test_get_candidate_view_returns_candidate_prompt_fields() -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "alternatives": ["firmware engineer", "embedded developer"],
                "confidence": 0.94,
                "evidence": ["CV headline: Embedded Software Engineer"],
            },
            "education": {
                "min_level": "bachelor",
                "accepted_fields": ["electrical engineering", "mechatronics"],
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
                },
                {
                    "name": "dutch",
                    "strength": "exposure",
                    "confidence": 0.4,
                    "evidence": ["Basic professional communication"],
                },
            ],
            "technical_experience": {
                "technical_core_features": [
                    {
                        "name": "embedded c",
                        "strength": "core",
                        "confidence": 0.95,
                        "evidence": ["Built production firmware in C"],
                    },
                    {
                        "name": "rtos",
                        "strength": "strong",
                        "confidence": 0.85,
                        "evidence": ["Worked with FreeRTOS"],
                    },
                ],
                "technologies": [
                    {
                        "name": "can",
                        "strength": "strong",
                        "confidence": 0.8,
                        "evidence": ["CAN bus integration"],
                    },
                    {
                        "name": "python",
                        "strength": "secondary",
                        "confidence": 0.7,
                        "evidence": ["Test automation tooling"],
                    },
                ],
            },
        }
    )

    assert EligibilityInputView.get_candidate_view(candidate_profile) == {
        "{{CANDIDATE_ROLE_PRIMARY}}": "embedded software engineer",
        "{{CANDIDATE_ROLE_ALTERNATIVES}}": "firmware engineer, embedded developer",
        "{{CANDIDATE_EDUCATION_MIN_LEVEL}}": "bachelor",
        "{{CANDIDATE_EDUCATION_FIELDS}}": "electrical engineering, mechatronics",
        "{{CANDIDATE_LANGUAGES}}": "english (strong), dutch (exposure)",
        "{{CANDIDATE_MIN_YEARS}}": "7",
        "{{CANDIDATE_SENIORITY_BAND}}": "senior",
        "{{CANDIDATE_TECHNICAL_CORE_FEATURES}}": "- embedded c (core)\n- rtos (strong)",
        "{{CANDIDATE_TECHNOLOGIES}}": "- can (strong)\n- python (secondary)",
    }


def test_get_candidate_view_uses_explicit_defaults_for_missing_fields() -> None:
    candidate_profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "confidence": 0.94,
                "evidence": ["CV headline: Embedded Software Engineer"],
            },
        }
    )

    assert EligibilityInputView.get_candidate_view(candidate_profile) == {
        "{{CANDIDATE_ROLE_PRIMARY}}": "embedded software engineer",
        "{{CANDIDATE_ROLE_ALTERNATIVES}}": "none",
        "{{CANDIDATE_EDUCATION_MIN_LEVEL}}": "not specified",
        "{{CANDIDATE_EDUCATION_FIELDS}}": "not specified",
        "{{CANDIDATE_LANGUAGES}}": "not specified",
        "{{CANDIDATE_MIN_YEARS}}": "not specified",
        "{{CANDIDATE_SENIORITY_BAND}}": "not specified",
        "{{CANDIDATE_TECHNICAL_CORE_FEATURES}}": "not specified",
        "{{CANDIDATE_TECHNOLOGIES}}": "not specified",
    }


def test_get_job_view_returns_job_prompt_fields() -> None:
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

    assert EligibilityInputView.get_job_view(vacancy_profile) == {
        "{{VACANCY_ROLE_PRIMARY}}": "embedded software designer",
        "{{VACANCY_ROLE_ALTERNATIVES}}": "embedded engineer",
        "{{VACANCY_EDUCATION_MIN_LEVEL}}": "bachelor",
        "{{VACANCY_EDUCATION_FIELDS}}": "electrical engineering, computer science",
        "{{VACANCY_REQUIRED_LANGUAGES}}": "english",
        "{{VACANCY_PREFERRED_LANGUAGES}}": "dutch",
        "{{VACANCY_MIN_YEARS}}": "5",
        "{{VACANCY_SENIORITY_BAND}}": "senior",
        "{{VACANCY_TECHNICAL_CORE_FEATURES}}": "- embedded c (required)\n- rtos (preferred)",
        "{{VACANCY_TECHNOLOGIES}}": "- can (required)\n- python (preferred)",
    }


def test_get_job_view_uses_explicit_defaults_for_missing_fields() -> None:
    vacancy_profile = VacancyProfile.model_validate(
        {
            "role_titles": {
                "primary": "embedded software designer",
                "confidence": 0.9,
                "evidence": ["Vacancy title"],
            }
        }
    )

    assert EligibilityInputView.get_job_view(vacancy_profile) == {
        "{{VACANCY_ROLE_PRIMARY}}": "embedded software designer",
        "{{VACANCY_ROLE_ALTERNATIVES}}": "none",
        "{{VACANCY_EDUCATION_MIN_LEVEL}}": "not specified",
        "{{VACANCY_EDUCATION_FIELDS}}": "not specified",
        "{{VACANCY_REQUIRED_LANGUAGES}}": "not specified",
        "{{VACANCY_PREFERRED_LANGUAGES}}": "not specified",
        "{{VACANCY_MIN_YEARS}}": "not specified",
        "{{VACANCY_SENIORITY_BAND}}": "not specified",
        "{{VACANCY_TECHNICAL_CORE_FEATURES}}": "not specified",
        "{{VACANCY_TECHNOLOGIES}}": "not specified",
    }
