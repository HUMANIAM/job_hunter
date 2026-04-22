from __future__ import annotations

import logging

from ui.candidate.repo import (
    CandidateProfileRepo,
    CandidateProfileRepoError,
)
from ui.shared.profile_types import SupportedCandidateProfile

logger = logging.getLogger(__name__)


class CandidateProfileServiceError(Exception):
    pass


class CandidateProfileService:
    def __init__(self, repo: CandidateProfileRepo) -> None:
        self._repo = repo

    def get_profile(self, profile_id: int) -> SupportedCandidateProfile:
        if profile_id <= 0:
            raise CandidateProfileServiceError("profile_id must be a positive integer")

        try:
            return self._repo.read(profile_id)
        except CandidateProfileRepoError as exc:
            logger.exception("Failed to load candidate profile %s", profile_id)
            raise CandidateProfileServiceError(
                f"Failed to load candidate profile {profile_id}"
            ) from exc
