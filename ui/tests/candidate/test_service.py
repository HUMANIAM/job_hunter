from __future__ import annotations

import logging

import pytest

from ui.candidate import service as candidate_service
from ui.candidate.repo import CandidateProfileRepoError


class StubCandidateProfileRepo:
    def __init__(
        self,
        *,
        result: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.requested_profile_id: int | None = None

    def read(self, profile_id: int) -> object:
        self.requested_profile_id = profile_id
        if self._error is not None:
            raise self._error
        return self._result


class TestCandidateProfileService:
    def test_get_profile_returns_repo_result(self) -> None:
        expected_profile = object()
        repo = StubCandidateProfileRepo(result=expected_profile)
        service = candidate_service.CandidateProfileService(repo=repo)

        result = service.get_profile(42)

        assert repo.requested_profile_id == 42
        assert result is expected_profile

    def test_get_profile_rejects_non_positive_id(self) -> None:
        repo = StubCandidateProfileRepo()
        service = candidate_service.CandidateProfileService(repo=repo)

        with pytest.raises(
            candidate_service.CandidateProfileServiceError,
            match="profile_id must be a positive integer",
        ):
            service.get_profile(0)

        assert repo.requested_profile_id is None

    def test_get_profile_wraps_repo_error_and_logs(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        repo = StubCandidateProfileRepo(
            error=CandidateProfileRepoError("candidate profile payload broke"),
        )
        service = candidate_service.CandidateProfileService(repo=repo)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(
                candidate_service.CandidateProfileServiceError,
                match="Failed to load candidate profile 7",
            ):
                service.get_profile(7)

        assert repo.requested_profile_id == 7
        assert "Failed to load candidate profile 7" in caplog.text
        assert "candidate profile payload broke" in caplog.text
