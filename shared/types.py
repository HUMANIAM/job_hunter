from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


SeniorityBand = Literal["junior", "standard", "senior", "lead", "principal"]
Strength = Literal["core", "strong", "secondary", "exposure"]


class ForbidExtra(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupportedField(ForbidExtra):
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)


__all__ = [
    "ForbidExtra",
    "SeniorityBand",
    "Strength",
    "SupportedField",
]
