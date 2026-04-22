from __future__ import annotations

from ui.candidate.repo import CandidateProfileRepo
from ui.candidate.service import CandidateProfileService
from ui.shared.api import ApiClient

# Composition root: shared client plus feature repos/services for the UI process.
api_client = ApiClient()
candidate_profile_repo = CandidateProfileRepo(api_client=api_client)
candidate_profile_service = CandidateProfileService(repo=candidate_profile_repo)
