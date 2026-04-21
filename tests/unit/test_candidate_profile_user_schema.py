from __future__ import annotations

import pytest
from pydantic import ValidationError

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
)


def test_candidate_profile_user_schema_normalizes_feature_lists() -> None:
    profile = CandidateProfileUpdate.model_validate(
        {
            "role_titles": {
                "primary": " Senior Embedded Software Engineer ",
                "alternatives": [
                    "Lead Embedded Engineer",
                    "senior embedded software engineer",
                ],
            },
            "languages": [
                {
                    "name": " English ",
                    "strength": "strong",
                },
                {
                    "name": "english",
                    "strength": "secondary",
                },
                {
                    "name": " German ",
                    "strength": "exposure",
                },
            ],
            "domain_background": [
                {
                    "name": " Semiconductor ",
                    "strength": "strong",
                },
                {
                    "name": "semiconductor",
                    "strength": "secondary",
                },
            ],
        }
    )

    assert [(item.name, item.strength) for item in profile.languages] == [
        ("english", "strong"),
        ("german", "exposure"),
    ]
    assert [(item.name, item.strength) for item in profile.domain_background] == [
        ("semiconductor", "strong"),
    ]


def test_candidate_profile_user_schema_requires_at_least_one_update() -> None:
    with pytest.raises(
        ValidationError,
        match="at least one field must be provided for update",
    ):
        CandidateProfileUpdate.model_validate({})


def test_candidate_profile_create_schema_accepts_all_required_fields() -> None:
    profile = CandidateProfileCreate.model_validate(
        {
            "role_titles": {
                "primary": "Senior Embedded Software Engineer",
                "alternatives": ["Lead Embedded Engineer"],
            },
            "education": {
                "min_level": "Bachelor",
                "accepted_fields": ["Computer Science"],
            },
            "experience": {
                "min_years": 5,
                "seniority_band": "Senior",
            },
            "technical_experience": {
                "technical_core_features": [
                    {"name": "Embedded C", "strength": "core"},
                ],
                "technologies": [
                    {"name": "Python", "strength": "strong"},
                ],
            },
            "languages": [
                {"name": "English", "strength": "strong"},
            ],
            "domain_background": [
                {"name": "Semiconductor", "strength": "strong"},
            ],
        }
    )

    assert profile.role_titles.primary == "senior embedded software engineer"
    assert profile.education.min_level == "bachelor"
    assert profile.experience.min_years == 5
    assert profile.technical_experience.technical_core_features[0].name == "embedded c"
    assert profile.languages[0].name == "english"
    assert profile.domain_background[0].name == "semiconductor"


def test_candidate_profile_create_schema_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        CandidateProfileCreate.model_validate(
            {
                "role_titles": {
                    "primary": "Data Engineer",
                },
                "education": {},
                "experience": {},
                "technical_experience": {
                    "technical_core_features": [],
                    "technologies": [],
                },
                "languages": [],
            }
        )
