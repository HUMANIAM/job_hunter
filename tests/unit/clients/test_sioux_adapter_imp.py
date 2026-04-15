from __future__ import annotations

from types import ModuleType
import sys

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

from clients.sources.browser_listing_adapter import AdvanceDecision, PageAdvance
from clients.sources.sioux.adapter_imp import SiouxBrowserListingAdapter


class _FakePage:
    pass


class _FakeContext:
    def __init__(self) -> None:
        self.page = _FakePage()

    def new_page(self) -> _FakePage:
        return self.page


class _FakeBrowser:
    def __init__(self) -> None:
        self.context = _FakeContext()

    def new_context(self):
        class _Manager:
            def __enter__(self_nonlocal):
                return self.context

            def __exit__(self_nonlocal, exc_type, exc, tb):
                return None

        return _Manager()


def test_sioux_browser_listing_adapter_uses_typed_default_returns() -> None:
    adapter = SiouxBrowserListingAdapter()
    page = object()
    browser = _FakeBrowser()

    assert adapter.collect_job_links(browser, job_limit=10) == []
    assert adapter._get_job_links_from_page(page, "sioux page", job_limit=10) == set()
    assert adapter._get_page_advance(page) == PageAdvance(
        advance_decision=AdvanceDecision.STOP,
    )
    assert adapter._get_next_page(page, adapter._get_page_advance(page)) is page
