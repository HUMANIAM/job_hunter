from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError

from clients.sources.new_design import playwright_browser_access as playwright_module
from clients.sources.new_design.browser_access import BrowserAccessError
from clients.sources.new_design.playwright_browser_access import (
    PlaywrightBrowserAccess,
    PlaywrightDOMElement,
)


class FakeElementLocator:
    def __init__(self, attributes: dict[str, str]) -> None:
        self._attributes = attributes

    def get_attribute(self, name: str) -> str | None:
        return self._attributes.get(name)

    def inner_text(self) -> str:
        return ""

    def locator(self, selector: str) -> FakeElementLocator:
        return self


class FakeLocatorCollection:
    def __init__(self, locators: list[FakeElementLocator]) -> None:
        self._locators = locators

    def count(self) -> int:
        return len(self._locators)

    def nth(self, index: int) -> FakeElementLocator:
        return self._locators[index]


class FailingLocatorCollection:
    def count(self) -> int:
        raise PlaywrightError("locator count failed")

    def nth(self, index: int) -> FakeElementLocator:
        raise AssertionError("nth should not be called after count fails")


class FakePage:
    def __init__(
        self,
        collections: dict[str, FakeLocatorCollection],
        *,
        url: str = "https://example.test/current",
        html_content: str = "<html></html>",
    ) -> None:
        self._collections = collections
        self.url = url
        self._html_content = html_content
        self.queried_selectors: list[str] = []
        self.opened_urls: list[str] = []

    def locator(self, selector: str) -> FakeLocatorCollection:
        self.queried_selectors.append(selector)
        return self._collections[selector]

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.opened_urls.append(url)
        self.url = url

    def content(self) -> str:
        return self._html_content


class FailingPage(FakePage):
    def locator(self, selector: str) -> FailingLocatorCollection:
        self.queried_selectors.append(selector)
        return FailingLocatorCollection()


class FailingNavigationPage(FakePage):
    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        raise PlaywrightError("navigation failed")


class FailingContentPage(FakePage):
    def content(self) -> str:
        raise PlaywrightError("content failed")


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self._page = page
        self.new_page_calls = 0

    def new_page(self) -> FakePage:
        self.new_page_calls += 1
        return self._page


class FailingContext:
    def new_page(self) -> FakePage:
        raise PlaywrightError("new page failed")


class FailingElementLocator(FakeElementLocator):
    def get_attribute(self, name: str) -> str | None:
        raise PlaywrightError("attribute read failed")

    def inner_text(self) -> str:
        raise PlaywrightError("text read failed")


def test_find_elements_wraps_matching_locators_from_current_page() -> None:
    page = FakePage(
        {
            ".job": FakeLocatorCollection(
                [
                    FakeElementLocator({"href": "https://example.test/one"}),
                    FakeElementLocator({"href": "https://example.test/two"}),
                ]
            )
        }
    )
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    elements = browser_access.find_elements(".job")
    second_read = browser_access.find_elements(".job")

    assert context.new_page_calls == 1
    assert page.queried_selectors == [".job", ".job"]
    assert [element.get_attribute("href") for element in elements] == [
        "https://example.test/one",
        "https://example.test/two",
    ]
    assert [element.get_attribute("href") for element in second_read] == [
        "https://example.test/one",
        "https://example.test/two",
    ]


def test_dom_element_wraps_playwright_attribute_errors() -> None:
    element = PlaywrightDOMElement(FailingElementLocator({}))

    with pytest.raises(BrowserAccessError) as exc_info:
        element.get_attribute("href")

    assert "attribute" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_dom_element_wraps_playwright_text_errors() -> None:
    element = PlaywrightDOMElement(FailingElementLocator({}))

    with pytest.raises(BrowserAccessError) as exc_info:
        element.get_text()

    assert "text" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_find_elements_wraps_playwright_locator_errors() -> None:
    page = FailingPage({})
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    with pytest.raises(BrowserAccessError) as exc_info:
        browser_access.find_elements(".job")

    assert ".job" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_open_url_wraps_playwright_navigation_errors(monkeypatch) -> None:
    page = FakePage({})
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    def fail_open_and_prepare_page(*args, **kwargs) -> list[str]:
        raise PlaywrightError("navigation failed")

    monkeypatch.setattr(
        playwright_module,
        "open_and_prepare_page",
        fail_open_and_prepare_page,
    )

    with pytest.raises(BrowserAccessError) as exc_info:
        browser_access.open_url("https://example.test/jobs")

    assert "https://example.test/jobs" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_download_page_opens_url_and_returns_html() -> None:
    page = FakePage({}, html_content="<html><body>job</body></html>")
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    html = browser_access.download_page("https://example.test/jobs/1")

    assert html == "<html><body>job</body></html>"
    assert page.opened_urls == ["https://example.test/jobs/1"]
    assert page.url == "https://example.test/jobs/1"
    assert context.new_page_calls == 1


def test_download_page_wraps_playwright_navigation_errors() -> None:
    browser_access = PlaywrightBrowserAccess(FakeContext(FailingNavigationPage({})))

    with pytest.raises(BrowserAccessError) as exc_info:
        browser_access.download_page("https://example.test/jobs/1")

    assert "https://example.test/jobs/1" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_download_page_wraps_playwright_content_errors() -> None:
    page = FailingContentPage({})
    browser_access = PlaywrightBrowserAccess(FakeContext(page))

    with pytest.raises(BrowserAccessError) as exc_info:
        browser_access.download_page("https://example.test/jobs/1")

    assert "https://example.test/jobs/1" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_page_creation_wraps_playwright_errors() -> None:
    browser_access = PlaywrightBrowserAccess(FailingContext())

    with pytest.raises(BrowserAccessError) as exc_info:
        browser_access.current_url()

    assert "browser page" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, PlaywrightError)


def test_current_url_returns_active_page_url() -> None:
    page = FakePage({}, url="https://example.test/facet?page=2")
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    assert browser_access.current_url() == "https://example.test/facet?page=2"
    assert context.new_page_calls == 1
