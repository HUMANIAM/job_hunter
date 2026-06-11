from __future__ import annotations

from clients.sources.new_design.playwright_browser_access import (
    PlaywrightBrowserAccess,
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


class FakePage:
    def __init__(
        self,
        collections: dict[str, FakeLocatorCollection],
        *,
        url: str = "https://example.test/current",
    ) -> None:
        self._collections = collections
        self.url = url
        self.queried_selectors: list[str] = []

    def locator(self, selector: str) -> FakeLocatorCollection:
        self.queried_selectors.append(selector)
        return self._collections[selector]


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self._page = page
        self.new_page_calls = 0

    def new_page(self) -> FakePage:
        self.new_page_calls += 1
        return self._page


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


def test_current_url_returns_active_page_url() -> None:
    page = FakePage({}, url="https://example.test/facet?page=2")
    context = FakeContext(page)
    browser_access = PlaywrightBrowserAccess(context)

    assert browser_access.current_url() == "https://example.test/facet?page=2"
    assert context.new_page_calls == 1
