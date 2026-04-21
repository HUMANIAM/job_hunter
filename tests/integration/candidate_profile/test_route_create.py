from __future__ import annotations

from clients.candidate_profiling.candidate_profiling_model import CandidateProfileRecord
from tests.helpers.db import select_where_in


def test_create_candidate_profile_persists_and_returns_mapped_data(client) -> None:
    uploaded_cv_id = 888
    payload = {
        "role_titles": {
            "primary": "data engineer",
            "alternatives": ["analytics engineer"],
        },
        "education": {
            "min_level": "bachelor",
            "accepted_fields": ["computer science"],
        },
        "experience": {
            "min_years": 5,
            "seniority_band": "senior",
        },
        "technical_experience": {
            "technical_core_features": [
                {"name": "python", "strength": "core"},
            ],
            "technologies": [
                {"name": "postgresql", "strength": "strong"},
            ],
        },
        "languages": [
            {"name": "english", "strength": "strong"},
        ],
        "domain_background": [
            {"name": "healthcare", "strength": "secondary"},
        ],
    }

    support_fields = {"confidence": 1.0, "evidence": ["user input"]}
    expected_response = {
        "role_titles": {
            "primary": "data engineer",
            "alternatives": ["analytics engineer"],
            **support_fields,
        },
        "education": {
            "min_level": "bachelor",
            "accepted_fields": ["computer science"],
            **support_fields,
        },
        "experience": {
            "min_years": 5,
            "seniority_band": "senior",
            **support_fields,
        },
        "technical_experience": {
            "technical_core_features": [
                {
                    "name": "python",
                    "strength": "core",
                    **support_fields,
                }
            ],
            "technologies": [
                {
                    "name": "postgresql",
                    "strength": "strong",
                    **support_fields,
                }
            ],
        },
        "languages": [
            {
                "name": "english",
                "strength": "strong",
                **support_fields,
            }
        ],
        "domain_background": [
            {
                "name": "healthcare",
                "strength": "secondary",
                **support_fields,
            }
        ],
    }

    response = client.post(f"/candidate-profiles/{uploaded_cv_id}", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_response

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"uploaded_cv_id": [uploaded_cv_id]},
    )
    assert len(matched_items) == 1
    persisted_record = matched_items[0]

    assert persisted_record.role_title_primary == "data engineer"
    assert persisted_record.role_titles_json == expected_response["role_titles"]
    assert persisted_record.education_json == expected_response["education"]
    assert persisted_record.experience_json == expected_response["experience"]
    assert (
        persisted_record.technical_experience_json
        == expected_response["technical_experience"]
    )
    assert persisted_record.languages_json == expected_response["languages"]
    assert (
        persisted_record.domain_background_json
        == expected_response["domain_background"]
    )


def test_create_candidate_profile_rejects_missing_required_field(client) -> None:
    uploaded_cv_id = 889
    payload = {
        "role_titles": {
            "primary": "data engineer",
            "alternatives": ["analytics engineer"],
        },
        "education": {
            "min_level": "bachelor",
            "accepted_fields": ["computer science"],
        },
        "experience": {
            "min_years": 5,
            "seniority_band": "senior",
        },
        "technical_experience": {
            "technical_core_features": [
                {"name": "python", "strength": "core"},
            ],
            "technologies": [
                {"name": "postgresql", "strength": "strong"},
            ],
        },
        "languages": [
            {"name": "english", "strength": "strong"},
        ],
    }

    response = client.post(f"/candidate-profiles/{uploaded_cv_id}", json=payload)

    assert response.status_code == 422

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"uploaded_cv_id": [uploaded_cv_id]},
    )
    assert matched_items == []
