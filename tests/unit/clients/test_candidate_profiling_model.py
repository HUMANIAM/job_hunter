from __future__ import annotations

import pytest
from pydantic import ValidationError

from clients.candidate_profiling.candidate_profiling_model import CandidateProfile
from tests.data.candidate import make_candidate_profile


def test_candidate_profile_rejects_unknown_technical_experience_fields() -> None:
    payload = make_candidate_profile().model_dump(mode="json")
    payload["technical_experience"] = {"unexpected": []}

    with pytest.raises(ValidationError, match="unexpected"):
        CandidateProfile.model_validate(payload)
