from __future__ import annotations

from dataclasses import dataclass

import pytest


class StubApiClient:
    def __init__(
        self,
        *,
        payload: object | None = None,
        error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self._error = error
        self.requested_path: str | None = None

    def get_json(self, path: str, *, params: dict[str, object] | None = None) -> object:
        self.requested_path = path
        if self._error is not None:
            raise self._error
        return self._payload


@dataclass
class FakeApiSettings:
    BACKEND_BASE_URL: str = "http://localhost:8000"
    BACKEND_TIMEOUT_SECONDS: float = 1.0


@pytest.fixture
def patch_api_settings(monkeypatch: pytest.MonkeyPatch):
    def apply(module, **overrides) -> FakeApiSettings:
        settings = FakeApiSettings(**overrides)
        monkeypatch.setattr(module, "get_settings", lambda: settings)
        return settings

    return apply
