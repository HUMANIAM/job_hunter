from __future__ import annotations

from typing import Any

from ui.shared.api import ApiClient


PROFILE_PATH = "candidate-profiles"
class CandidateProfileRepo:
    def __init__(self, api_client: ApiClient) -> None:
        self._api_client = api_client

    def read(self, profile_id: int) -> dict[str, Any]:
        data = self._api_client.get_json(f"{PROFILE_PATH}/{profile_id}")
        if not isinstance(data, dict):
            raise TypeError("Expected candidate profile response to be a JSON object")
        return data
