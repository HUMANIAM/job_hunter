from __future__ import annotations

from unittest.mock import Mock

from clients.candidate_profiling import candidate_service
from clients.candidate_profiling.candidate_profile_schema import CandidateProfileUpdate
from tests.data.candidate import make_candidate_profile, make_candidate_profile_record


def test_update_candidate_profile_uses_mapper_before_repo_update(
    mock_session: Mock,
    monkeypatch,
) -> None:
    uploaded_cv_id = 42
    existing_record = make_candidate_profile_record(uploaded_cv_id=uploaded_cv_id)
    updated_record = make_candidate_profile_record(uploaded_cv_id=uploaded_cv_id)

    repo = Mock()
    repo.get_by_uploaded_cv_id.return_value = existing_record
    repo.update.return_value = updated_record
    monkeypatch.setattr(
        candidate_service,
        "CandidateProfileRepository",
        lambda: repo,
    )

    mapped_profile = make_candidate_profile(primary_role_title="data engineer")
    mapper = Mock(return_value=mapped_profile)
    monkeypatch.setattr(candidate_service, "map_candidate_profile_update", mapper)

    expected_read_schema = object()
    read_schema_mapper = Mock(return_value=expected_read_schema)
    monkeypatch.setattr(candidate_service, "_to_read_schema", read_schema_mapper)

    payload = CandidateProfileUpdate(role_titles={"primary": "data engineer"})

    result = candidate_service.update_candidate_profile(
        uploaded_cv_id=uploaded_cv_id,
        profile_update=payload,
        session=mock_session,
    )

    assert result is expected_read_schema
    repo.get_by_uploaded_cv_id.assert_called_once_with(
        session=mock_session,
        uploaded_cv_id=uploaded_cv_id,
    )
    mapper.assert_called_once_with(
        value=payload,
        existing_record=existing_record,
    )
    repo.update.assert_called_once_with(
        session=mock_session,
        record=existing_record,
        profile=mapped_profile,
        commit=True,
    )
    read_schema_mapper.assert_called_once_with(updated_record)
