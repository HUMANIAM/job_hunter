from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfileCreate,
    CandidateProfileRead,
    CandidateProfileUpdate,
)

from infra.db import get_session
from clients.candidate_profiling import candidate_service as service


router = APIRouter(prefix="/candidate-profiles", tags=["candidate-profiles"])


@router.post(
    "/{uploaded_cv_id}",
    response_model=CandidateProfileRead,
    status_code=status.HTTP_200_OK,
)
def create_candidate_profile(
    uploaded_cv_id: int,
    payload: CandidateProfileCreate,
    session: Session = Depends(get_session),
) -> CandidateProfileRead:
    record = service.create_candidate_profile(
        uploaded_cv_id=uploaded_cv_id,
        profile_create=payload,
        session=session,
    )
    return record


@router.get(
    "/{uploaded_cv_id}",
    response_model=CandidateProfileRead,
    status_code=status.HTTP_200_OK,
)
def read_candidate_profile(
    uploaded_cv_id: int,
    session: Session = Depends(get_session),
) -> CandidateProfileRead:
    record = service.read_candidate_profile(uploaded_cv_id=uploaded_cv_id, session=session)
    return record


@router.patch(
    "/{uploaded_cv_id}",
    response_model=CandidateProfileRead,
    status_code=status.HTTP_200_OK,
)
def update_candidate_profile(
    uploaded_cv_id: int,
    payload: CandidateProfileUpdate,
    session: Session = Depends(get_session),
) -> CandidateProfileRead:
    record = service.update_candidate_profile(
        uploaded_cv_id=uploaded_cv_id,
        profile_update=payload,
        session=session,
    )
    return record


@router.delete(
    "/{uploaded_cv_id}",
    response_model=CandidateProfileRead,
    status_code=status.HTTP_200_OK,
)
def delete_candidate_profile(
    uploaded_cv_id: int,
    session: Session = Depends(get_session),
) -> CandidateProfileRead:
    record = service.delete_candidate_profile(
        uploaded_cv_id=uploaded_cv_id,
        session=session,
    )
    return record
