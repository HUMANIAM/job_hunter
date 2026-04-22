from __future__ import annotations

import logging
from collections.abc import Mapping

from ui.shared.api import ApiClient, ApiError
from ui.candidate.profile_mapper import map_candidate_profile
from ui.shared.profile_types import SupportedCandidateProfile


PROFILE_PATH = "candidate-profiles"
logger = logging.getLogger(__name__)


class CandidateProfileRepoError(Exception):
    pass


class CandidateProfileRepo:
    def __init__(self, api_client: ApiClient) -> None:
        self._api_client = api_client

    def read(self, profile_id: int) -> SupportedCandidateProfile:
        try:
            data = self._api_client.get_json(f"{PROFILE_PATH}/{profile_id}")
        except ApiError as exc:
            logger.exception("Failed to fetch candidate profile %s", profile_id)
            raise CandidateProfileRepoError(
                f"Failed to fetch candidate profile {profile_id}"
            ) from exc

        try:
            if not isinstance(data, Mapping):
                raise TypeError("Expected candidate profile response to be a JSON object")
            return map_candidate_profile(data)
        except Exception as exc:
            logger.exception("Failed to parse candidate profile %s", profile_id)
            raise CandidateProfileRepoError(
                f"Invalid candidate profile payload for {profile_id}"
            ) from exc
