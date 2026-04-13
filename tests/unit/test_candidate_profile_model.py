from __future__ import annotations

import pytest
from pydantic import ValidationError

from clients.candidate_profiling.candidate_profile_model import CandidateProfile


def test_candidate_profile_normalizes_shared_sections() -> None:
    profile = CandidateProfile.model_validate(
        {
            "role_titles": {
                "primary": " Senior Embedded Software Engineer ",
                "alternatives": [
                    "Lead Embedded Engineer",
                    "senior embedded software engineer",
                ],
                "confidence": "0.93",
                "evidence": ["CV headline: Senior Embedded Software Engineer"],
            },
            "education": {
                "min_level": " Bachelor ",
                "accepted_fields": [
                    " Electrical Engineering ",
                    "electrical engineering",
                ],
                "confidence": 0.8,
                "evidence": ["BSc Electrical Engineering"],
            },
            "experience": {
                "min_years": "7",
                "seniority_band": " Senior ",
                "confidence": 0.88,
                "evidence": ["7 years embedded systems experience"],
            },
            "languages": [
                {
                    "name": " English ",
                    "strength": "strong",
                    "confidence": 0.75,
                    "evidence": ["Worked on international teams"],
                },
                {
                    "name": "english",
                    "strength": "secondary",
                    "confidence": 0.5,
                    "evidence": ["Daily technical communication in English"],
                },
                {
                    "name": " German ",
                    "strength": "exposure",
                    "confidence": 0.35,
                    "evidence": ["Basic German course"],
                },
            ],
            "technical_experience": {
                "technical_core_features": [
                    {
                        "name": " Python ",
                        "strength": "core",
                        "confidence": 0.9,
                        "evidence": ["Python and CAN experience"],
                    },
                    {
                        "name": "python",
                        "strength": "strong",
                        "confidence": 0.8,
                        "evidence": ["Backend services in Python"],
                    },
                    {
                        "name": " CAN ",
                        "strength": "strong",
                        "confidence": 0.85,
                        "evidence": ["Worked with CAN diagnostics"],
                    },
                ],
            },
            "domain_background": [
                {
                    "name": " Semiconductor ",
                    "strength": "strong",
                    "confidence": 0.7,
                    "evidence": ["ASML semiconductor systems"],
                },
                {
                    "name": "semiconductor",
                    "strength": "secondary",
                    "confidence": 0.5,
                    "evidence": ["EUV lithography systems"],
                },
            ],
        }
    )

    assert profile.role_titles.primary == "senior embedded software engineer"
    assert profile.role_titles.alternatives == ["lead embedded engineer"]
    assert profile.education.min_level == "bachelor"
    assert profile.education.accepted_fields == ["electrical engineering"]
    assert profile.experience.min_years == 7
    assert profile.experience.seniority_band == "senior"
    assert [(item.name, item.strength) for item in profile.languages] == [
        ("english", "strong"),
        ("german", "exposure"),
    ]
    assert [
        (item.name, item.strength)
        for item in profile.technical_experience.technical_core_features
    ] == [("python", "core"), ("can", "strong")]
    assert [(item.name, item.strength) for item in profile.domain_background] == [
        ("semiconductor", "strong"),
    ]


def test_candidate_profile_requires_evidence_for_feature_items() -> None:
    with pytest.raises(
        ValidationError,
        match="evidence must not be empty",
    ):
        CandidateProfile.model_validate(
            {
                "role_titles": {
                    "primary": "embedded software engineer",
                    "confidence": 0.91,
                    "evidence": ["CV headline: Embedded Software Engineer"],
                },
                "technical_experience": {
                    "technical_core_features": [
                        {
                            "name": "python",
                            "strength": "core",
                            "confidence": 0.8,
                            "evidence": [],
                        }
                    ]
                },
            }
        )


def test_candidate_profile_rejects_unknown_seniority_band() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        CandidateProfile.model_validate(
            {
                "role_titles": {
                    "primary": "embedded software engineer",
                    "confidence": 0.91,
                    "evidence": ["CV headline: Embedded Software Engineer"],
                },
                "experience": {
                    "seniority_band": "medior",
                    "confidence": 0.8,
                    "evidence": ["Senior embedded systems experience"],
                },
            }
        )
