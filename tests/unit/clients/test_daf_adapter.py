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

from clients.sources.daf.adapter import DafClientAdapter


class FakeAnchor:
    def __init__(self, href: str | None) -> None:
        self.href = href

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


class FakeAnchorList:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._anchors = [FakeAnchor(href) for href in hrefs]

    def count(self) -> int:
        return len(self._anchors)

    def nth(self, index: int) -> FakeAnchor:
        return self._anchors[index]


class MissingElement:
    def count(self) -> int:
        return 0

    def get_attribute(self, name: str) -> None:
        return None

    def click(self) -> None:
        raise AssertionError("click should not be called on a missing element")


class FakeElement:
    def __init__(
        self,
        *,
        href: str | None = None,
        data_page: str | None = None,
        disabled: str | None = None,
        aria_disabled: str | None = None,
        class_name: str | None = None,
    ) -> None:
        self.href = href
        self.data_page = data_page
        self.disabled = disabled
        self.aria_disabled = aria_disabled
        self.class_name = class_name
        self.clicked = False

    def count(self) -> int:
        return 1

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        if name == "data-page":
            return self.data_page
        if name == "disabled":
            return self.disabled
        if name == "aria-disabled":
            return self.aria_disabled
        if name == "class":
            return self.class_name
        raise AssertionError(f"unexpected attribute lookup: {name}")

    def click(self) -> None:
        self.clicked = True


class FakeSelectorResult:
    def __init__(self, element: FakeElement | MissingElement | None = None) -> None:
        self.first = element if element is not None else MissingElement()


class FakePage:
    def __init__(
        self,
        *,
        url: str,
        hrefs: list[str | None] | None = None,
        selector_map: dict[str, FakeElement] | None = None,
    ) -> None:
        self.url = url
        self._hrefs = hrefs or []
        self._selector_map = selector_map or {}
        self.wait_calls: list[int] = []

    def locator(self, selector: str):
        if selector == "a.vacancy-item__link[href]":
            return FakeAnchorList(self._hrefs)
        return FakeSelectorResult(self._selector_map.get(selector))

    def wait_for_timeout(self, delay_ms: int) -> None:
        self.wait_calls.append(delay_ms)


def test_collect_job_links_from_page_keeps_live_daf_job_urls() -> None:
    adapter = DafClientAdapter()
    page = FakePage(
        url=(
            "https://www.daf.com/en/working-at-daf/vacancies"
            "?Page=1&functionlevel=Professionals&region=Netherlands"
        ),
        hrefs=[
            "/en/working-at-daf/vacancies/open-application",
            "/en/working-at-daf/vacancies/monteur-elektrisch-pkf-truckfabriek",
            "https://www.daf.com/en/working-at-daf/vacancies/monteur-mechanisch-motorenfabriek",
        ],
    )

    links = adapter._collect_job_links_from_page(
        page,
        "daf nl professionals listing page 1",
        job_limit=10,
    )

    assert links == {
        "https://www.daf.com/en/working-at-daf/vacancies/monteur-elektrisch-pkf-truckfabriek",
        "https://www.daf.com/en/working-at-daf/vacancies/monteur-mechanisch-motorenfabriek",
    }


def test_get_next_page_url_detects_click_based_next_link() -> None:
    adapter = DafClientAdapter()
    page = FakePage(
        url=(
            "https://www.daf.com/en/working-at-daf/vacancies"
            "?Page=1&functionlevel=Professionals&region=Netherlands"
        ),
        selector_map={
            "a.page-link.page-link--next": FakeElement(data_page="next"),
        },
    )

    next_page = adapter._get_next_page_url(page)

    assert next_page == "__CLICK_NEXT__"


def test_click_next_page_clicks_click_based_next_link() -> None:
    adapter = DafClientAdapter()
    next_link = FakeElement(data_page="next", class_name="page-link page-link--next")
    page = FakePage(
        url=(
            "https://www.daf.com/en/working-at-daf/vacancies"
            "?Page=1&functionlevel=Professionals&region=Netherlands"
        ),
        selector_map={
            "a.page-link.page-link--next": next_link,
        },
    )

    moved = adapter._click_next_page(page)

    assert moved is True
    assert next_link.clicked is True
    assert page.wait_calls == [1500]
