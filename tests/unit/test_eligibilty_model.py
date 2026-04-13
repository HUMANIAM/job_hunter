from __future__ import annotations

import pytest
from pydantic import ValidationError

from clients.eligibility.eligibility_response_model import EligibilityResponse


def test_eligibility_response_accepts_valid_assessments() -> None:
    response = EligibilityResponse.model_validate(
        {
            "eligibility_score": 0.84,
            "decision": "eligible",
            "blocker_reasons": [],
            "support_reasons": ["role titles and languages align"],
            "field_assessments": [
                {
                    "field": "role_titles",
                    "decision": "match",
                    "score": 0.95,
                    "evidence": ["primary titles match closely"],
                },
                {
                    "field": "languages",
                    "decision": "partial",
                    "score": 0.6,
                    "evidence": ["required english is present"],
                },
            ],
        }
    )

    assert response.eligibility_score == 0.84
    assert response.decision == "eligible"
    assert response.field_assessments[0].field == "role_titles"
    assert response.field_assessments[1].decision == "partial"


def test_eligibility_response_rejects_scores_outside_unit_interval() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 1"):
        EligibilityResponse.model_validate(
            {
                "eligibility_score": 1.1,
                "decision": "eligible",
                "blocker_reasons": [],
                "support_reasons": [],
                "field_assessments": [],
            }
        )


def test_eligibility_response_rejects_invalid_field_assessment_score() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        EligibilityResponse.model_validate(
            {
                "eligibility_score": 0.4,
                "decision": "uncertain",
                "blocker_reasons": [],
                "support_reasons": [],
                "field_assessments": [
                    {
                        "field": "experience",
                        "decision": "unknown",
                        "score": -0.01,
                        "evidence": [],
                    }
                ],
            }
        )
