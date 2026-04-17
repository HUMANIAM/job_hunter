from __future__ import annotations

from unittest.mock import Mock

from clients.candidate_profiling.candidate_repo import (
    CandidateProfileRepository,
    _profile_to_json_columns,
)
from tests.unit.clients.data.candidate import (
    make_candidate_profile,
    make_candidate_profile_record,
)


def test_profile_to_json_columns() -> None:
    profile = make_candidate_profile()

    assert _profile_to_json_columns(profile) == {
        "role_titles_json": profile.role_titles.model_dump(mode="json"),
        "education_json": profile.education.model_dump(mode="json"),
        "experience_json": profile.experience.model_dump(mode="json"),
        "technical_experience_json": profile.technical_experience.model_dump(
            mode="json"
        ),
        "languages_json": [item.model_dump(mode="json") for item in profile.languages],
        "domain_background_json": [
            item.model_dump(mode="json") for item in profile.domain_background
        ],
    }


def test_create_candidate_profile(mock_session: Mock) -> None:
    profile = make_candidate_profile()
    uploaded_cv_id = 1
    expected_json_columns = _profile_to_json_columns(profile)

    record = CandidateProfileRepository().create(
        session=mock_session,
        uploaded_cv_id=uploaded_cv_id,
        profile=profile,
        commit=True,
    )

    assert record.id == 1
    assert record.uploaded_cv_id == uploaded_cv_id
    assert record.role_title_primary == profile.role_titles.primary
    for field_name, expected_value in expected_json_columns.items():
        assert getattr(record, field_name) == expected_value

    mock_session.add.assert_called_once_with(record)
    mock_session.flush.assert_called_once_with()
    mock_session.refresh.assert_called_once_with(record)
    mock_session.commit.assert_called_once_with()
    mock_session.rollback.assert_not_called()


def test_get_by_uploaded_cv_id_returns_record(
    mock_session: Mock,
    set_exec_first,
) -> None:
    uploaded_cv_id = 1
    expected_record = make_candidate_profile_record(
        id=10,
        uploaded_cv_id=uploaded_cv_id,
    )
    exec_result = set_exec_first(mock_session, expected_record)

    record = CandidateProfileRepository().get_by_uploaded_cv_id(
        session=mock_session,
        uploaded_cv_id=uploaded_cv_id,
    )

    assert record == expected_record
    mock_session.exec.assert_called_once()
    exec_result.first.assert_called_once_with()


def test_update_candidate_profile(mock_session: Mock) -> None:
    original_record = make_candidate_profile_record()
    profile = make_candidate_profile()
    expected_json_columns = _profile_to_json_columns(profile)

    record = CandidateProfileRepository().update(
        session=mock_session,
        record=original_record,
        profile=profile,
        commit=True,
    )

    assert record is original_record
    assert record.id == 1
    assert record.uploaded_cv_id == 1
    assert record.role_title_primary == profile.role_titles.primary
    for field_name, expected_value in expected_json_columns.items():
        assert getattr(record, field_name) == expected_value

    mock_session.add.assert_called_once_with(record)
    mock_session.flush.assert_called_once_with()
    mock_session.refresh.assert_called_once_with(record)
    mock_session.commit.assert_called_once_with()
    mock_session.rollback.assert_not_called()


def test_delete_candidate_profile(mock_session: Mock) -> None:
    record = make_candidate_profile_record()

    deleted_record = CandidateProfileRepository().delete(
        session=mock_session,
        record=record,
        commit=True,
    )

    assert deleted_record is record
    assert deleted_record.id == 1
    assert deleted_record.uploaded_cv_id == 1

    mock_session.delete.assert_called_once_with(record)
    mock_session.flush.assert_called_once_with()
    mock_session.commit.assert_called_once_with()
    mock_session.rollback.assert_not_called()
