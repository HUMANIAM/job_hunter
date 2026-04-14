from __future__ import annotations

from types import ModuleType
import sys

import pytest

if "playwright.sync_api" not in sys.modules:
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: None
    sync_api.Browser = object
    sync_api.Page = object
    sync_api.Playwright = object

    playwright = ModuleType("playwright")
    playwright.sync_api = sync_api

    sys.modules["playwright"] = playwright
    sys.modules["playwright.sync_api"] = sync_api

from clients.clients import Client
from clients.registry import get_client_adapter
from clients.sources.asml.adapter import AsmlClientAdapter
from clients.sources.sioux.adapter import SiouxClientAdapter


def test_get_client_adapter_returns_registered_asml_adapter() -> None:
    adapter = get_client_adapter(Client.ASML)

    assert isinstance(adapter, AsmlClientAdapter)


def test_get_client_adapter_returns_registered_sioux_adapter() -> None:
    adapter = get_client_adapter(Client.SIOUX)

    assert isinstance(adapter, SiouxClientAdapter)


def test_get_client_adapter_raises_clear_error_for_unknown_client() -> None:
    with pytest.raises(ValueError, match="No adapter registered for client: unknown"):
        get_client_adapter("unknown")  # type: ignore[arg-type]
