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

from clients.sources.browser_listing_adapter import AdvanceDecision, PageAdvance
from clients.sources.vanderlande.adapter import VanderlandeClientAdapter


class _FakeContext:
    def __init__(self, page: object) -> None:
        self.page = page
        self.new_page_calls = 0

    def new_page(self) -> object:
        self.new_page_calls += 1
        return self.page


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
    def __init__(self, *, url: str, hrefs: list[str | None]) -> None:
        self.url = url
        self._hrefs = hrefs

    def locator(self, selector: str) -> _FakeAnchorList:
        assert selector == "a[data-automation-id='jobTitle'][href]"
        return _FakeAnchorList(self._hrefs)


class _MissingElement:
    def count(self) -> int:
        return 0

    def get_attribute(self, name: str) -> None:
        return None

    def evaluate(self, script: str) -> str:
        raise AssertionError("evaluate should not be called")

    def click(self) -> None:
        raise AssertionError("click should not be called")


class _FakeNextElement:
    def __init__(
        self,
        *,
        tag_name: str = "button",
        href: str | None = None,
        disabled: str | None = None,
        aria_disabled: str | None = None,
        class_name: str = "",
    ) -> None:
        self.tag_name = tag_name
        self.href = href
        self.disabled = disabled
        self.aria_disabled = aria_disabled
        self.class_name = class_name
        self.clicked = False

    def count(self) -> int:
        return 1

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        if name == "disabled":
            return self.disabled
        if name == "aria-disabled":
            return self.aria_disabled
        if name == "class":
            return self.class_name
        raise AssertionError(f"unexpected attribute: {name}")

    def evaluate(self, script: str) -> str:
        assert script == "(el) => el.tagName.toLowerCase()"
        return self.tag_name

    def click(self) -> None:
        self.clicked = True


class _FakeSelectorResult:
    def __init__(self, element: _FakeNextElement | None = None) -> None:
        self.first = element if element is not None else _MissingElement()


class _FakePaginationPage:
    def __init__(self, *, url: str, next_element: _FakeNextElement | None) -> None:
        self.url = url
        self.next_element = next_element

    def locator(self, selector: str) -> _FakeSelectorResult | _FakeAnchorList:
        if selector == "a[data-automation-id='jobTitle'][href]":
            return _FakeAnchorList([])
        assert selector in {
            "button[aria-label='next']",
            "button[data-uxi-element-id='next']",
            "button[aria-label='Next']",
            "a[aria-label='Next']",
        }
        if self.next_element is None:
            return _FakeSelectorResult()
        return _FakeSelectorResult(self.next_element)


class _FakeClickPage(_FakePaginationPage):
    def __init__(self, *, url: str, next_element: _FakeNextElement | None) -> None:
        super().__init__(url=url, next_element=next_element)
        self.wait_calls: list[int] = []

    def wait_for_timeout(self, timeout: int) -> None:
        self.wait_calls.append(timeout)


def test_collect_job_links_in_context_uses_context_page(monkeypatch) -> None:
    adapter = VanderlandeClientAdapter()
    page = object()
    context = _FakeContext(page)
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
        lambda page_obj, context_label, *, job_limit: (
            listing_calls.append((page_obj, context_label, job_limit))
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
    assert open_calls == [(page, adapter.entry_url)]
    assert listing_calls == [(page, adapter.listing_label, 5)]


def test_get_job_links_from_page_filters_and_strips_query_string() -> None:
    adapter = VanderlandeClientAdapter()
    page = _FakeListingPage(
        url=adapter.entry_url,
        hrefs=[
            "/en-US/careers/job/a-role?ref=listing",
            "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/b-role?foo=1",
            "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job-alert",
            None,
        ],
    )

    links = adapter._get_job_links_from_page(
        page,
        "vanderlande page 1",
        job_limit=10,
    )

    assert links == {
        "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/a-role",
        "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers/job/b-role",
    }


def test_get_page_advance_returns_click_for_button_next() -> None:
    adapter = VanderlandeClientAdapter()
    page = _FakePaginationPage(
        url=adapter.entry_url,
        next_element=_FakeNextElement(tag_name="button"),
    )

    assert adapter._get_page_advance(page) == PageAdvance(
        advance_decision=AdvanceDecision.CLICK,
    )


def test_get_next_page_clicks_next_button_and_waits_1500_ms() -> None:
    adapter = VanderlandeClientAdapter()
    next_element = _FakeNextElement(tag_name="button")
    page = _FakeClickPage(url=adapter.entry_url, next_element=next_element)

    next_page = adapter._get_next_page(
        page,
        PageAdvance(advance_decision=AdvanceDecision.CLICK),
    )

    assert next_page is page
    assert next_element.clicked is True
    assert page.wait_calls == [1500]


@pytest.mark.parametrize(
    ("renderer_result", "title", "expected_title", "expected_html"),
    [
        (None, "Original", "Original", "<html>raw</html>"),
        (("Rendered", "<html>rendered</html>"), "Original", "Rendered", "<html>rendered</html>"),
        ((None, "<html>rendered</html>"), "Original", "Original", "<html>rendered</html>"),
    ],
)
def test_transform_downloaded_html_delegates_to_renderer(
    monkeypatch,
    renderer_result: tuple[str | None, str] | None,
    title: str | None,
    expected_title: str | None,
    expected_html: str,
) -> None:
    adapter = VanderlandeClientAdapter()
    calls: list[str] = []

    monkeypatch.setattr(
        "clients.sources.vanderlande.adapter.render_vanderlande_job_html",
        lambda html_content: calls.append(html_content) or renderer_result,
    )

    transformed_title, transformed_html = adapter.transform_downloaded_html(
        url="https://example.com/job",
        title=title,
        html_content="<html>raw</html>",
    )

    assert calls == ["<html>raw</html>"]
    assert transformed_title == expected_title
    assert transformed_html == expected_html
