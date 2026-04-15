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

from clients.sources.sioux import adapter as sioux_adapter_module
from clients.sources.sioux.adapter import SiouxClientAdapter


class _FakeAnchor:
    def __init__(self, href: str | None) -> None:
        self.href = href

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


class _FakeAnchorList:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._anchors = [_FakeAnchor(href) for href in hrefs]

    def count(self) -> int:
        return len(self._anchors)

    def nth(self, index: int) -> _FakeAnchor:
        return self._anchors[index]


class _FakePage:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._hrefs = hrefs

    def locator(self, selector: str) -> _FakeAnchorList:
        assert selector == "a.act-item-job-overview"
        return _FakeAnchorList(self._hrefs)


class _MissingElement:
    def count(self) -> int:
        return 0

    def get_attribute(self, name: str) -> None:
        return None


class _FakeNextElement:
    def __init__(self, href: str | None) -> None:
        self.href = href

    def count(self) -> int:
        return 1

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


class _FakeSelectorResult:
    def __init__(self, element: _FakeNextElement | _MissingElement | None = None) -> None:
        self.first = element if element is not None else _MissingElement()


class _FakePaginationPage:
    def __init__(self, next_href: str | None = None) -> None:
        self._next_href = next_href

    def locator(self, selector: str) -> _FakeSelectorResult:
        assert selector == "div.overview-paging-controls a.paging-item-next"
        if self._next_href is None:
            return _FakeSelectorResult()
        return _FakeSelectorResult(_FakeNextElement(self._next_href))


class _ExplodingPaginationPage:
    def locator(self, selector: str):
        assert selector == "div.overview-paging-controls a.paging-item-next"
        raise RuntimeError("boom")


def test_collect_job_links_from_page_keeps_live_sioux_job_urls() -> None:
    adapter = SiouxClientAdapter()
    page = _FakePage(
        [
            "/vacancies/embedded-software-engineer.html",
            "https://vacancy.sioux.eu/vacancies/system-architect.html",
            "/",
            None,
        ]
    )

    links = adapter._collect_job_links_from_page(
        page,
        "sioux listing page 1",
        job_limit=10,
    )

    assert links == {
        "https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        "https://vacancy.sioux.eu/vacancies/system-architect.html",
    }


def test_collect_links_for_facet_reuses_the_provided_page(monkeypatch) -> None:
    adapter = SiouxClientAdapter()
    page = object()
    open_calls: list[tuple[object, str]] = []
    listing_calls: list[tuple[object, str, int, int]] = []

    monkeypatch.setattr(
        adapter,
        "_open_page",
        lambda page_obj, url: open_calls.append((page_obj, url)),
    )
    monkeypatch.setattr(
        adapter,
        "_collect_links_from_paginated_listing",
        lambda page_obj, context, expected_count=None, *, job_limit: (
            listing_calls.append((page_obj, context, expected_count, job_limit))
            or {"https://vacancy.sioux.eu/vacancies/software-only.html"}
        ),
    )

    links = adapter._collect_links_for_facet(
        page,
        "Software",
        "https://example.com/software",
        4,
        job_limit=7,
    )

    assert links == {"https://vacancy.sioux.eu/vacancies/software-only.html"}
    assert open_calls == [(page, "https://example.com/software")]
    assert listing_calls == [(page, "facet 'Software'", 4, 7)]


def test_get_next_page_url_resolves_relative_next_link() -> None:
    adapter = SiouxClientAdapter()
    page = _FakePaginationPage("/vacancies?page=2")

    next_page = adapter._get_next_page_url(page)

    assert next_page == "https://vacancy.sioux.eu/vacancies?page=2"


def test_get_next_page_url_logs_selector_errors(monkeypatch) -> None:
    adapter = SiouxClientAdapter()
    page = _ExplodingPaginationPage()
    messages: list[str] = []

    monkeypatch.setattr(sioux_adapter_module, "log", messages.append)

    next_page = adapter._get_next_page_url(page)

    assert next_page is None
    assert messages == [
        "next page detection: selector 'div.overview-paging-controls "
        "a.paging-item-next' raised RuntimeError: boom"
    ]
