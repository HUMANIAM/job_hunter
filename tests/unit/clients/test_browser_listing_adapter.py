from __future__ import annotations

from types import SimpleNamespace
from types import ModuleType
from urllib.parse import urljoin
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

from clients.sources import browser_listing_adapter as browser_listing_adapter_module
from clients.sources.browser_listing_adapter import (
    AdvanceDecision,
    BrowserListingAdapter,
    PageAdvance,
)


class UrlFollowingBrowserListingAdapter(BrowserListingAdapter):
    entry_url = "https://example.com/jobs"
    listing_label = "example listing"
    results_ready_selectors = ("a[href]",)
    next_page = object()

    def _get_job_links_from_page(
        self,
        page: object,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return set()

    def _get_page_advance(self, page: object) -> PageAdvance:
        return PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://example.com/jobs?page=2",
        )

    def _collect_job_links_in_context(
        self,
        context: object,
        page: object,
        *,
        job_limit: int,
    ) -> list[str]:
        return []

    def _get_next_page(self, page: object, page_advance: PageAdvance) -> object:
        assert page_advance == PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://example.com/jobs?page=2",
        )
        return self.next_page


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


class _FakeListingPage:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._hrefs = hrefs

    def locator(self, selector: str) -> _FakeAnchorList:
        assert selector == "a[href]"
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
        assert selector == "a[rel='next']"
        if self._next_href is None:
            return _FakeSelectorResult()
        return _FakeSelectorResult(_FakeNextElement(self._next_href))


class _MutablePaginationPage:
    def __init__(self, url: str) -> None:
        self.url = url


def test_advance_decision_values_are_explicit() -> None:
    assert AdvanceDecision.FOLLOW_URL == "follow_url"
    assert AdvanceDecision.CLICK == "click"
    assert AdvanceDecision.STOP == "stop"


def test_page_advance_carries_both_advance_decision_and_next_page_url() -> None:
    page_advance = UrlFollowingBrowserListingAdapter()._get_page_advance(object())

    assert page_advance == PageAdvance(
        advance_decision=AdvanceDecision.FOLLOW_URL,
        next_page_url="https://example.com/jobs?page=2",
    )


def test_open_page_uses_shared_browser_listing_configuration(monkeypatch) -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = SimpleNamespace(url="https://example.com/jobs?page=1")
    open_calls: list[tuple[object, str, tuple[str, ...], tuple[str, ...]]] = []
    messages: list[str] = []

    monkeypatch.setattr(
        browser_listing_adapter_module,
        "open_and_prepare_page",
        lambda page_obj, url, *, wait_for, click_if_visible_selectors: (
            open_calls.append(
                (
                    page_obj,
                    url,
                    tuple(wait_for),
                    tuple(click_if_visible_selectors),
                )
            )
            or ["button.cookie-accept"]
        ),
    )
    monkeypatch.setattr(browser_listing_adapter_module, "log", messages.append)
    adapter.cookie_accept_selectors = ("button.cookie-accept",)

    adapter._open_page(page, "https://example.com/jobs?page=1")

    assert open_calls == [
        (
            page,
            "https://example.com/jobs?page=1",
            ("a[href]",),
            ("button.cookie-accept",),
        )
    ]
    assert messages == [
        "accepted cookie banner selectors: ['button.cookie-accept']",
        "current page url: https://example.com/jobs?page=1",
    ]


def test_get_next_page_executes_page_advance_and_returns_next_page() -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page_advance = adapter._get_page_advance(object())

    assert adapter._get_next_page(object(), page_advance) is adapter.next_page


def test_collect_job_links_from_page_common_filters_and_normalizes_urls() -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = _FakeListingPage(
        [
            "/jobs/alpha",
            "https://example.com/jobs/beta",
            "/about",
            None,
        ]
    )

    links = adapter._collect_job_links_from_page_common(
        page,
        log_context="example listing page 1",
        job_limit=10,
        candidates_selector="a[href]",
        found_label="anchor elements",
        normalize_href=lambda href: urljoin("https://example.com/base", href),
        is_job_url=lambda url: "/jobs/" in url,
    )

    assert links == {
        "https://example.com/jobs/alpha",
        "https://example.com/jobs/beta",
    }


def test_get_page_advance_common_returns_follow_url_when_next_href_exists() -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = _FakePaginationPage("/jobs?page=2")

    page_advance = adapter._get_page_advance_common(
        page,
        next_selectors=("a[rel='next']",),
        normalize_next_href=lambda href: urljoin("https://example.com/jobs", href),
        is_click_next_control=lambda _element: False,
    )

    assert page_advance == PageAdvance(
        advance_decision=AdvanceDecision.FOLLOW_URL,
        next_page_url="https://example.com/jobs?page=2",
    )


def test_get_next_page_common_opens_follow_url_and_returns_same_page(
    monkeypatch,
) -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = object()
    open_calls: list[tuple[object, str]] = []

    monkeypatch.setattr(
        adapter,
        "_open_page",
        lambda page_obj, url: open_calls.append((page_obj, url)),
    )

    next_page = adapter._get_next_page_common(
        page,
        PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://example.com/jobs?page=2",
        ),
    )

    assert next_page is page
    assert open_calls == [(page, "https://example.com/jobs?page=2")]


def test_collect_links_from_paginated_listing_common_follows_until_stop(
    monkeypatch,
) -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = _MutablePaginationPage("https://example.com/jobs?page=1")
    transitions: list[str] = []

    monkeypatch.setattr(
        adapter,
        "_get_job_links_from_page",
        lambda page_obj, log_context, *, job_limit: {
            "https://example.com/jobs?page=1": {
                "https://example.com/jobs/alpha",
            },
            "https://example.com/jobs?page=2": {
                "https://example.com/jobs/beta",
            },
        }[page_obj.url],
    )
    monkeypatch.setattr(
        adapter,
        "_get_page_advance",
        lambda page_obj: (
            PageAdvance(
                advance_decision=AdvanceDecision.FOLLOW_URL,
                next_page_url="https://example.com/jobs?page=2",
            )
            if page_obj.url == "https://example.com/jobs?page=1"
            else PageAdvance(advance_decision=AdvanceDecision.STOP)
        ),
    )
    monkeypatch.setattr(
        adapter,
        "_get_next_page",
        lambda page_obj, page_advance: (
            transitions.append(page_advance.next_page_url or "")
            or setattr(page_obj, "url", page_advance.next_page_url)
            or page_obj
        ),
    )

    links = adapter._collect_links_from_paginated_listing(
        page,
        "example listing",
        expected_count=2,
        job_limit=10,
    )

    assert links == {
        "https://example.com/jobs/alpha",
        "https://example.com/jobs/beta",
    }
    assert transitions == ["https://example.com/jobs?page=2"]
