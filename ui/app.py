from __future__ import annotations

from ui.candidate.repo import CandidateProfileRepo
from ui.shared.api import ApiClient

# Composition root: shared client and feature repos for the UI process.
api_client = ApiClient()
candidate_profile_repo = CandidateProfileRepo(api_client=api_client)
