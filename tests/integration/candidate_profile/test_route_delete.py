from __future__ import annotations

from clients.candidate_profiling.candidate_profiling_model import CandidateProfileRecord
from tests.data.candidate import make_candidate_profile_endpoint_record
from tests.helpers.db import add_record, select_where_in


def test_delete_candidate_profile_deletes_record_and_returns_data(client) -> None:
    uploaded_cv_id = 777
    persisted_record = make_candidate_profile_endpoint_record(
        uploaded_cv_id=uploaded_cv_id
    )

    add_record(client.session, persisted_record)

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"uploaded_cv_id": [uploaded_cv_id]},
    )
    assert len(matched_items) == 1
    persisted_record = matched_items[0]

    response = client.delete(f"/candidate-profiles/{uploaded_cv_id}")

    assert response.status_code == 200
    assert response.json() == {
        "role_titles": persisted_record.role_titles_json,
        "education": persisted_record.education_json,
        "experience": persisted_record.experience_json,
        "technical_experience": persisted_record.technical_experience_json,
        "languages": persisted_record.languages_json,
        "domain_background": persisted_record.domain_background_json,
    }

    matched_items = select_where_in(
        client.session,
        CandidateProfileRecord,
        {"uploaded_cv_id": [uploaded_cv_id]},
    )
    assert matched_items == []


def test_delete_candidate_profile_returns_not_found_for_unknown_cv_id(client) -> None:
    uploaded_cv_id = 999_999

    response = client.delete(f"/candidate-profiles/{uploaded_cv_id}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": (
            f"delete: Candidate profile not found for uploaded_cv_id={uploaded_cv_id}"
        )
    }
