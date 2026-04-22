from __future__ import annotations

from importlib import reload

import ui.app as app_module
from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.shared.api import ApiClient


def test_build_services_wires_candidate_profile_service() -> None:
    module = reload(app_module)
    module.build_services.clear()
    services = module.build_services()

    assert isinstance(services, module.AppServices)
    assert isinstance(services.candidate_profile_service, CandidateProfileService)
    assert isinstance(services.candidate_profile_service._repo, CandidateProfileRepo)
    assert isinstance(
        services.candidate_profile_service._repo._api_client,
        ApiClient,
    )
