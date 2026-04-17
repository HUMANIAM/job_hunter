from __future__ import annotations

from sqlmodel import Session, select

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile,
    CandidateProfileRecord,
)
from shared.db_repo import commit_if_requested_or_raise


def _profile_to_json_columns(profile: CandidateProfile) -> dict[str, object]:
    return {
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
            **_profile_to_json_columns(profile),
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

    def get_by_uploaded_cv_id(
        self,
        *,
        session: Session,
        uploaded_cv_id: int,
    ) -> CandidateProfileRecord | None:
        statement = select(CandidateProfileRecord).where(
            CandidateProfileRecord.uploaded_cv_id == uploaded_cv_id
        )
        return session.exec(statement).first()

    def update(
        self,
        *,
        session: Session,
        record: CandidateProfileRecord,
        profile: CandidateProfile,
        commit: bool = True,
    ) -> CandidateProfileRecord:
        record.role_title_primary = profile.role_titles.primary

        for field_name, value in _profile_to_json_columns(profile).items():
            setattr(record, field_name, value)

        def _persist() -> CandidateProfileRecord:
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

        return commit_if_requested_or_raise(
            session,
            commit=commit,
            operation="update",
            entity="candidate_profile",
            fn=_persist,
        )

    def delete(
        self,
        *,
        session: Session,
        record: CandidateProfileRecord,
        commit: bool = True,
    ) -> CandidateProfileRecord:
        def _persist() -> CandidateProfileRecord:
            session.delete(record)
            session.flush()
            return record

        return commit_if_requested_or_raise(
            session,
            commit=commit,
            operation="delete",
            entity="candidate_profile",
            fn=_persist,
        )
