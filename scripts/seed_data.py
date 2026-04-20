from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from clients.candidate_profiling.candidate_profiling_model import (
    CandidateProfile,
    CandidateProfileRecord,
)
from clients.candidate_profiling.candidate_repo import CandidateProfileRepository
from infra.db import create_db_and_tables, get_engine
from tests.data.candidate import make_candidate_profile_endpoint_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the database with a candidate profile record."
    )
    parser.add_argument(
        "--uploaded-cv-id",
        type=int,
        default=501,
        help="uploaded_cv_id value for the seeded candidate profile (default: 501).",
    )
    return parser.parse_args()


def _to_candidate_profile(record: CandidateProfileRecord) -> CandidateProfile:
    return CandidateProfile.model_validate(
        {
            "role_titles": record.role_titles_json,
            "education": record.education_json,
            "experience": record.experience_json,
            "technical_experience": record.technical_experience_json,
            "languages": record.languages_json,
            "domain_background": record.domain_background_json,
        }
    )


def upsert_candidate_profile_record(
    session: Session,
    *,
    uploaded_cv_id: int,
    seed_source: CandidateProfileRecord,
) -> CandidateProfileRecord:
    repo = CandidateProfileRepository()
    profile = _to_candidate_profile(seed_source)

    existing = repo.get_by_uploaded_cv_id(
        session=session,
        uploaded_cv_id=uploaded_cv_id,
    )
    if existing is None:
        return repo.create(
            session=session,
            uploaded_cv_id=uploaded_cv_id,
            profile=profile,
            commit=True,
        )

    return repo.update(
        session=session,
        record=existing,
        profile=profile,
        commit=True,
    )


def seed_candidate_profile(
    session: Session, *, uploaded_cv_id: int
) -> CandidateProfileRecord:
    seed_source = make_candidate_profile_endpoint_record(uploaded_cv_id=uploaded_cv_id)

    return upsert_candidate_profile_record(
        session,
        uploaded_cv_id=uploaded_cv_id,
        seed_source=seed_source,
    )


def seed_data(*, uploaded_cv_id: int = 501) -> int:
    create_db_and_tables()
    with Session(get_engine()) as session:
        try:
            # Seed candidate profile record.
            record = seed_candidate_profile(session, uploaded_cv_id=uploaded_cv_id)
            print(
                "Seeded candidate profile "
                f"id={record.id} uploaded_cv_id={record.uploaded_cv_id}"
            )
            return 0

        except Exception as error:
            print(f"Seeding candidate profile failed: {error}", file=sys.stderr)
            return 1


def main() -> int:
    args = parse_args()
    return seed_data(uploaded_cv_id=args.uploaded_cv_id)

if __name__ == "__main__":
    raise SystemExit(main())
