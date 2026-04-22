from __future__ import annotations

from importlib import reload

import ui.app as app_module
from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.shared.api import ApiClient


def test_app_wires_candidate_profile_service() -> None:
    module = reload(app_module)

    assert isinstance(module.api_client, ApiClient)
    assert isinstance(module.candidate_profile_repo, CandidateProfileRepo)
    assert isinstance(module.candidate_profile_service, CandidateProfileService)
    assert module.candidate_profile_repo._api_client is module.api_client
    assert module.candidate_profile_service._repo is module.candidate_profile_repo
