from __future__ import annotations

from dataclasses import dataclass

import pytest


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
