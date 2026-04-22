from __future__ import annotations

from importlib import reload

import ui.pages.home as home_module
from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.shared.api import ApiClient


def test_home_wires_candidate_profile_service() -> None:
    module = reload(home_module)

    module.get_candidate_profile_service.clear()
    service = module.get_candidate_profile_service()

    assert isinstance(service, CandidateProfileService)
    assert isinstance(service._repo, CandidateProfileRepo)
    assert isinstance(service._repo._api_client, ApiClient)
