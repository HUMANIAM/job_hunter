from __future__ import annotations

import logging

import pytest

from tests.data.candidate import make_candidate_profile_endpoint_record
from ui.candidate import repo as candidate_repo
from ui.shared.api import ApiError
from ui.shared.profile_types import SupportedCandidateProfile
from ui.tests.conftest import StubApiClient


class TestCandidateProfileRepo:
    def test_read_returns_supported_candidate_profile(self) -> None:
        persisted_record = make_candidate_profile_endpoint_record(uploaded_cv_id=42)
        payload = {
            "role_titles": persisted_record.role_titles_json,
            "education": persisted_record.education_json,
            "experience": persisted_record.experience_json,
            "technical_experience": persisted_record.technical_experience_json,
            "languages": persisted_record.languages_json,
            "domain_background": persisted_record.domain_background_json,
        }
        api_client = StubApiClient(payload=payload)
        repo = candidate_repo.CandidateProfileRepo(api_client=api_client)

        result = repo.read(42)

        assert api_client.requested_path == "candidate-profiles/42"
        assert isinstance(result, SupportedCandidateProfile)
        assert result.role_titles.primary == payload["role_titles"]["primary"]
        assert result.languages[0].name == payload["languages"][0]["name"]

    def test_read_raises_repo_error_and_logs_for_api_failure(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        api_client = StubApiClient(error=ApiError("backend down"))
        repo = candidate_repo.CandidateProfileRepo(api_client=api_client)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(
                candidate_repo.CandidateProfileRepoError,
                match="Failed to fetch candidate profile 7",
            ):
                repo.read(7)

        assert "Failed to fetch candidate profile 7" in caplog.text
        assert "backend down" in caplog.text

    def test_read_raises_repo_error_and_logs_for_invalid_payload(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        api_client = StubApiClient(payload={"role_titles": "not-an-object"})
        repo = candidate_repo.CandidateProfileRepo(api_client=api_client)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(
                candidate_repo.CandidateProfileRepoError,
                match="Invalid candidate profile payload for 7",
            ):
                repo.read(7)

        assert "Failed to parse candidate profile 7" in caplog.text
        assert "role_titles must be an object" in caplog.text
