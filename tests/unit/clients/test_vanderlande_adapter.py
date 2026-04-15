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

from clients.sources.vanderlande.adapter import VanderlandeClientAdapter


class FakePage:
    def __init__(self, *, url: str) -> None:
        self.url = url


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self.page = page
        self.new_page_calls = 0

    def new_page(self) -> FakePage:
        self.new_page_calls += 1
        return self.page


def test_collect_job_links_in_context_uses_context_page(monkeypatch) -> None:
    adapter = VanderlandeClientAdapter()
    page = FakePage(
        url=(
            "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers"
            "?locationCountry=9696868b09c64d52a62ee13b052383cc"
            "&workerSubType=65d289099a0c104a3602035a812e138b"
        )
    )
    context = FakeContext(page)
    open_calls: list[tuple[object, str]] = []
    listing_calls: list[tuple[object, str, int]] = []

    monkeypatch.setattr(
        adapter,
        "_open_page",
        lambda page_obj, url: open_calls.append((page_obj, url)),
    )
    monkeypatch.setattr(
        adapter,
        "_collect_links_from_paginated_listing",
        lambda page_obj, context, *, job_limit: (
            listing_calls.append((page_obj, context, job_limit))
            or {
                "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/b-role",
                "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/a-role",
            }
        ),
    )

    links = adapter._collect_job_links_in_context(context, job_limit=5)

    assert links == [
        "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/a-role",
        "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/b-role",
    ]
    assert context.new_page_calls == 1
    assert open_calls == [(page, adapter.ENTRY_URL)]
    assert listing_calls == [(page, "vanderlande nl listing", 5)]
