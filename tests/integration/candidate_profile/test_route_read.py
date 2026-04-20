from __future__ import annotations

from clients.candidate_profiling.candidate_profiling_model import CandidateProfileRecord
from tests.data.candidate import make_candidate_profile_endpoint_record
from tests.helpers.db import add_record, select_where_in


def test_read_candidate_profile_returns_persisted_data(
    client,
) -> None:
    uploaded_cv_id = 501
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

    response = client.get(f"/candidate-profiles/{uploaded_cv_id}")

    assert response.status_code == 200
    print(response.json())
    assert response.json() == {
        "role_titles": persisted_record.role_titles_json,
        "education": persisted_record.education_json,
        "experience": persisted_record.experience_json,
        "technical_experience": persisted_record.technical_experience_json,
        "languages": persisted_record.languages_json,
        "domain_background": persisted_record.domain_background_json,
    }
