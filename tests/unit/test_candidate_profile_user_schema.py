from __future__ import annotations

from clients.candidate_profiling.candidate_profile_schema import (
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
