from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import Field as PydanticField
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from shared.profiling_model import (
    Education,
    Experience,
    ForbidExtra,
    RoleTitles,
    StrengthFeature,
    TechnicalExperience,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CandidateProfile(ForbidExtra):
    """Business model for a profiled candidate."""

    role_titles: RoleTitles
    education: Education = PydanticField(default_factory=Education)
    experience: Experience = PydanticField(default_factory=Experience)
    technical_experience: TechnicalExperience = PydanticField(
        default_factory=TechnicalExperience
    )
    languages: List[StrengthFeature] = PydanticField(default_factory=list)
    domain_background: List[StrengthFeature] = PydanticField(default_factory=list)


class CandidateProfileRecord(SQLModel, table=True):
    """Persistence model for a candidate profile row."""

    __tablename__ = "candidate_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    uploaded_cv_id: int = Field(nullable=False, index=True)

    role_title_primary: Optional[str] = Field(default=None, index=True)

    role_titles_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    education_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    experience_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    technical_experience_json: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    languages_json: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    domain_background_json: List[Dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )

    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


__all__ = [
    "CandidateProfile",
    "CandidateProfileRecord",
]
