from __future__ import annotations

from clients.sources.new_design.browser_access import (
    BrowserAccess,
    DOMElement,
    Selector,
    SelectorList,
)
from clients.sources.new_design.sioux import sioux_config as config
from clients.sources.new_design.sioux.sioux_vacancy_source import SiouxVacancySource
from clients.sources.new_design.sioux.sioux_vacancy_source_provider import (
    create_sioux_vacancy_source_provider,
)
from clients.sources.new_design.tests.data.dom import FakeDOMElement
from clients.sources.new_design.types import VacancyLinks


class FakeBrowserAccess(BrowserAccess):
    def __init__(
        self,
        elements_by_url: dict[str, dict[Selector, list[DOMElement]]],
    ) -> None:
        self._elements_by_url = elements_by_url
        self._current_url = ""

    def open_url(
        self,
        url: str,
        *,
        wait_for_selectors: SelectorList = (),
        click_if_visible_selectors: SelectorList = (),
    ) -> None:
        self._current_url = url

    def download_page(self, url: str) -> str:
        self._current_url = url
        return ""

    def find_elements(self, selector: Selector) -> list[DOMElement]:
        return self._elements_by_url[self._current_url].get(selector, [])

    def current_url(self) -> str:
        return self._current_url


def test_sioux_provider_creates_source_with_supplied_browser_access() -> None:
    facet_url = "https://vacancy.sioux.eu/software"
    browser_access = FakeBrowserAccess(
        {
            config.SIOUX_ENTRY_URL: {
                config.SIOUX_DISCIPLINE_FACET_SELECTOR: [
                    FakeDOMElement(
                        attributes={"href": facet_url},
                        text_by_selector={
                            ".filter-item-link-name": "Software",
                            ".filter-item-link-count": "1",
                        },
                    ),
                ],
            },
            facet_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/one.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [],
            },
        }
    )
    provider = create_sioux_vacancy_source_provider(browser_access=browser_access)

    source = provider()

    assert isinstance(source, SiouxVacancySource)
    assert source.get_vacancy_links() == VacancyLinks(
        links={"https://vacancy.sioux.eu/vacancies/one.html"}
    )
