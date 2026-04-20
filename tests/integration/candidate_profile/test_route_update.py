from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfileRecord,
)
from tests.data.candidate import make_candidate_profile_endpoint_record
from tests.helpers.db import add_record, select_where_in


def test_update_candidate_profile_persists_and_returns_mapped_data(client) -> None:
    uploaded_cv_id = (uuid4().int % 2_000_000_000) or 1
    persisted_record = make_candidate_profile_endpoint_record(
        uploaded_cv_id=uploaded_cv_id
    )
    persisted_record.id = None
    add_record(client.session, persisted_record)
    expected_existing_education = deepcopy(persisted_record.education_json)
    expected_existing_experience = deepcopy(persisted_record.experience_json)
    expected_existing_technical_experience = deepcopy(
        persisted_record.technical_experience_json
    )
    expected_existing_languages = deepcopy(persisted_record.languages_json)
    expected_existing_domain_background = deepcopy(
        persisted_record.domain_background_json
    )

    payload = {
        "role_titles": {
            "primary": "data engineer",
            "alternatives": ["analytics engineer"],
        },
    }

    support_fields = {"confidence": 1.0, "evidence": ["user input"]}
    expected_response = {
        "role_titles": {
            "primary": "data engineer",
            "alternatives": ["analytics engineer"],
            **support_fields,
        },
        "education": expected_existing_education,
        "experience": expected_existing_experience,
        "technical_experience": expected_existing_technical_experience,
        "languages": expected_existing_languages,
        "domain_background": expected_existing_domain_background,
    }

    response = client.put(f"/candidate-profiles/{uploaded_cv_id}", json=payload)

    assert response.status_code == 200
    assert response.json() == expected_response

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"id": [persisted_record.id]},
    )
    assert len(matched_items) == 1
    updated_record = matched_items[0]

    assert updated_record.role_title_primary == "data engineer"
    assert updated_record.role_titles_json == expected_response["role_titles"]
    assert updated_record.education_json == expected_response["education"]
    assert updated_record.experience_json == expected_response["experience"]
    assert (
        updated_record.technical_experience_json
        == expected_response["technical_experience"]
    )
    assert updated_record.languages_json == expected_response["languages"]
    assert (
        updated_record.domain_background_json
        == expected_response["domain_background"]
    )


def test_update_candidate_profile_rejects_empty_payload(client) -> None:
    uploaded_cv_id = (uuid4().int % 2_000_000_000) or 1
    persisted_record = make_candidate_profile_endpoint_record(
        uploaded_cv_id=uploaded_cv_id
    )
    persisted_record.id = None
    add_record(client.session, persisted_record)
    original_record_id = persisted_record.id
    original_role_titles = deepcopy(persisted_record.role_titles_json)

    response = client.put(f"/candidate-profiles/{uploaded_cv_id}", json={})

    assert response.status_code == 422
    assert "at least one field must be provided for update" in str(response.json())

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"id": [original_record_id]},
    )
    assert len(matched_items) == 1
    assert matched_items[0].role_titles_json == original_role_titles
