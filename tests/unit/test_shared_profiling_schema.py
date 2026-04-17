from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.profiling_schema import (
    ClassifiedTexts,
    LegalAndComplianceConstraints,
    MobilityConstraints,
    RequirementTexts,
    WorkModeConstraints,
)


@pytest.mark.parametrize(
    ("model", "payload", "message"),
    [
        (
            ClassifiedTexts,
            {"required": ["python"], "evidence": []},
            "evidence must not be empty when classified texts are set",
        ),
        (
            RequirementTexts,
            {"required": ["semiconductor"], "evidence": []},
            "evidence must not be empty when requirement texts are set",
        ),
        (
            WorkModeConstraints,
            {"remote": True, "evidence": []},
            "evidence must not be empty when work mode constraints are set",
        ),
        (
            MobilityConstraints,
            {"travel_required": True, "evidence": []},
            "evidence must not be empty when mobility constraints are set",
        ),
        (
            LegalAndComplianceConstraints,
            {"work_authorization_required": True, "evidence": []},
            "evidence must not be empty when legal and compliance constraints are set",
        ),
    ],
)
def test_shared_profiling_models_require_evidence_when_populated(
    model: type[object],
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        model.model_validate(payload)
