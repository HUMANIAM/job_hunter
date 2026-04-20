from __future__ import annotations

from unittest.mock import Mock

from clients.candidate_profiling.candidate_profiling_model import CandidateProfile
from scripts import seed_data
from tests.data.candidate import (
    make_candidate_profile_endpoint_record,
    make_candidate_profile_record,
)


def test_upsert_candidate_profile_record_uses_create_when_missing(
    monkeypatch,
) -> None:
    session = object()
    uploaded_cv_id = 501
    seed_source = make_candidate_profile_endpoint_record(uploaded_cv_id=uploaded_cv_id)

    repo = Mock()
    repo.get_by_uploaded_cv_id.return_value = None
    created_record = make_candidate_profile_record(uploaded_cv_id=uploaded_cv_id)
    repo.create.return_value = created_record
    monkeypatch.setattr(seed_data, "CandidateProfileRepository", lambda: repo)

    result = seed_data.upsert_candidate_profile_record(
        session,
        uploaded_cv_id=uploaded_cv_id,
        seed_source=seed_source,
    )

    assert result is created_record
    repo.get_by_uploaded_cv_id.assert_called_once_with(
        session=session,
        uploaded_cv_id=uploaded_cv_id,
    )
    repo.create.assert_called_once()
    repo.update.assert_not_called()

    create_kwargs = repo.create.call_args.kwargs
    assert create_kwargs["session"] is session
    assert create_kwargs["uploaded_cv_id"] == uploaded_cv_id
    assert isinstance(create_kwargs["profile"], CandidateProfile)
    assert create_kwargs["commit"] is True


def test_upsert_candidate_profile_record_uses_update_when_existing(
    monkeypatch,
) -> None:
    session = object()
    uploaded_cv_id = 501
    seed_source = make_candidate_profile_endpoint_record(uploaded_cv_id=uploaded_cv_id)
    existing_record = make_candidate_profile_record(uploaded_cv_id=uploaded_cv_id)

    repo = Mock()
    repo.get_by_uploaded_cv_id.return_value = existing_record
    updated_record = make_candidate_profile_record(uploaded_cv_id=uploaded_cv_id)
    repo.update.return_value = updated_record
    monkeypatch.setattr(seed_data, "CandidateProfileRepository", lambda: repo)

    result = seed_data.upsert_candidate_profile_record(
        session,
        uploaded_cv_id=uploaded_cv_id,
        seed_source=seed_source,
    )

    assert result is updated_record
    repo.get_by_uploaded_cv_id.assert_called_once_with(
        session=session,
        uploaded_cv_id=uploaded_cv_id,
    )
    repo.create.assert_not_called()
    repo.update.assert_called_once()

    update_kwargs = repo.update.call_args.kwargs
    assert update_kwargs["session"] is session
    assert update_kwargs["record"] is existing_record
    assert isinstance(update_kwargs["profile"], CandidateProfile)
    assert update_kwargs["commit"] is True
