from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

EligibilityDecision = Literal["eligible", "uncertain", "not_eligible"]
FieldDecision = Literal["match", "partial", "mismatch", "unknown"]


class FieldAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal[
        "role_titles",
        "education",
        "experience",
        "languages",
        "technical_core_features",
        "technologies",
    ]
    decision: FieldDecision
    score: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = Field(default_factory=list)


class EligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligibility_score: float = Field(ge=0.0, le=1.0)
    decision: EligibilityDecision
    blocker_reasons: List[str] = Field(default_factory=list)
    support_reasons: List[str] = Field(default_factory=list)
    field_assessments: List[FieldAssessment] = Field(default_factory=list)