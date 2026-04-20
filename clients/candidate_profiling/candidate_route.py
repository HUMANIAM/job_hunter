from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from clients.candidate_profiling.candidate_profile_schema import (
    CandidateProfileRead,
    CandidateProfileUpdate,
)

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile as CandidateProfileModel,
    CandidateProfileRecord,
)
from clients.candidate_profiling.candidate_repo import CandidateProfileRepository
from infra.db import get_session
from ranking import service
from shared.profiling_model import (
    Education as EducationModel,
    Experience as ExperienceModel,
    RoleTitles as RoleTitlesModel,
    StrengthFeature as StrengthFeatureModel,
    TechnicalExperience as TechnicalExperienceModel,
)
from shared.profiling_schema import StrengthFeatureBase
from clients.candidate_profiling import candidate_service as service


router = APIRouter(prefix="/candidate-profiles", tags=["candidate-profiles"])

# _USER_INPUT_EVIDENCE = ["user input"]


# def _support_kwargs() -> dict[str, object]:
#     return {
#         "confidence": 1.0,
#         "evidence": _USER_INPUT_EVIDENCE,
#     }


# def _to_strength_feature_model(
#     feature: StrengthFeatureBase,
# ) -> StrengthFeatureModel:
#     return StrengthFeatureModel(
#         name=feature.name,
#         strength=feature.strength,
#         **_support_kwargs(),
#     )

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


# @router.put(
#     "/{uploaded_cv_id}",
#     response_model=CandidateProfileRead,
#     status_code=status.HTTP_200_OK,
# )
# def update_candidate_profile(
#     uploaded_cv_id: int,
#     payload: CandidateProfileUserSchema,
#     session: Session = Depends(get_session),
# ) -> CandidateProfileRead:
#     repo = CandidateProfileRepository()
#     record = repo.get_by_uploaded_cv_id(
#         session=session,
#         uploaded_cv_id=uploaded_cv_id,
#     )
#     if record is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Candidate profile not found for uploaded_cv_id={uploaded_cv_id}",
#         )

#     updated_record = repo.update(
#         session=session,
#         record=record,
#         profile=_to_domain_profile(payload),
#         commit=True,
#     )
#     return _to_read_schema(updated_record)