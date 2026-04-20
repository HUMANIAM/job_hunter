from sqlmodel import Session

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfileRead,
    CandidateProfileUpdate,
)
from clients.candidate_profiling.candidate_repo import CandidateProfileRepository
from clients.candidate_profiling.candidate_types_mapper import (
    _to_read_schema,
    map_candidate_profile_update,
)
from shared.error_helpers import ensure_found


def read_candidate_profile(uploaded_cv_id: int, session: Session) -> CandidateProfileRead:
    repo = CandidateProfileRepository()
    record = repo.get_by_uploaded_cv_id(
        session=session,
        uploaded_cv_id=uploaded_cv_id,
    )

    record = ensure_found(
        record,
        resource="Candidate profile",
        lookup_field="uploaded_cv_id",
        lookup_value=uploaded_cv_id,
        operation="read",
    )

    return _to_read_schema(record)


def update_candidate_profile(
    uploaded_cv_id: int,
    profile_update: CandidateProfileUpdate,
    session: Session,
) -> CandidateProfileRead:
    repo = CandidateProfileRepository()
    record = repo.get_by_uploaded_cv_id(
        session=session,
        uploaded_cv_id=uploaded_cv_id,
    )
    record = ensure_found(
        record,
        resource="Candidate profile",
        lookup_field="uploaded_cv_id",
        lookup_value=uploaded_cv_id,
        operation="update",
    )
    mapped_profile = map_candidate_profile_update(
        value=profile_update,
        existing_record=record,
    )

    updated_record = repo.update(
        session=session,
        record=record,
        profile=mapped_profile,
        commit=True,
    )

    return _to_read_schema(updated_record)
