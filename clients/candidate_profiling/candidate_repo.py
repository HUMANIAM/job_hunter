from __future__ import annotations

from sqlmodel import Session

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile,
    CandidateProfileRecord,
)
from shared.db_repo import commit_if_requested_or_raise


class CandidateProfileRepository:
    def create(
        self,
        *,
        session: Session,
        uploaded_cv_id: int,
        profile: CandidateProfile,
        commit: bool = True,
    ) -> CandidateProfileRecord:
        record = CandidateProfileRecord(
            uploaded_cv_id=uploaded_cv_id,
            role_title_primary=profile.role_titles.primary,
            role_titles_json=profile.role_titles.model_dump(mode="json"),
            education_json=profile.education.model_dump(mode="json"),
            experience_json=profile.experience.model_dump(mode="json"),
            technical_experience_json=profile.technical_experience.model_dump(
                mode="json"
            ),
            languages_json=[
                item.model_dump(mode="json") for item in profile.languages
            ],
            domain_background_json=[
                item.model_dump(mode="json") for item in profile.domain_background
            ],
        )

        def _persist() -> CandidateProfileRecord:
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

        return commit_if_requested_or_raise(
            session,
            commit=commit,
            operation="create",
            entity="candidate_profile",
            fn=_persist,
        )
