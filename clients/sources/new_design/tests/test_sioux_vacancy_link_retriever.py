from __future__ import annotations

from clients.sources.new_design import vacancy_link_retriever as vlr
from clients.sources.new_design.browser_access import (
    BrowserAccess,
    DOMElement,
    Selector,
    SelectorList,
)
from clients.sources.new_design.sioux import sioux_config as config
from clients.sources.new_design.sioux.sioux_vacancy_link_retriever import (
    SiouxFacetCursor,
    SiouxVacancyLinkRetriever,
)
from clients.sources.new_design.tests.data.dom import FakeDOMElement
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks


class FakeBrowserAccess(BrowserAccess):
    def __init__(
        self,
        elements_by_url: dict[str, dict[Selector, list[DOMElement]]],
        *,
        pages_by_url: dict[str, str] | None = None,
    ) -> None:
        self._elements_by_url = elements_by_url
        self._pages_by_url = pages_by_url or {}
        self._current_url = ""
        self.open_calls: list[
            tuple[str, tuple[Selector, ...], tuple[Selector, ...]]
        ] = []
        self.download_calls: list[str] = []

    def open_url(
        self,
        url: str,
        *,
        wait_for_selectors: SelectorList = (),
        click_if_visible_selectors: SelectorList = (),
    ) -> None:
        self._current_url = url
        self.open_calls.append(
            (
                url,
                tuple(wait_for_selectors),
                tuple(click_if_visible_selectors),
            )
        )

    def download_page(self, url: str) -> str:
        self._current_url = url
        self.download_calls.append(url)
        return self._pages_by_url[url]

    def find_elements(self, selector: Selector) -> list[DOMElement]:
        return self._elements_by_url[self._current_url].get(selector, [])

    def current_url(self) -> str:
        return self._current_url


def test_get_initial_cursor_discovers_discipline_facets() -> None:
    browser_access = FakeBrowserAccess(
        {
            config.SIOUX_ENTRY_URL: {
                config.SIOUX_DISCIPLINE_FACET_SELECTOR: [
                    FakeDOMElement(
                        attributes={"href": "/software"},
                        text_by_selector={
                            ".filter-item-link-name": "Software",
                            ".filter-item-link-count": "2",
                        },
                    ),
                ]
            }
        }
    )
    retriever = SiouxVacancyLinkRetriever(browser_access=browser_access)

    cursor = retriever._get_initial_cursor(criteria=VacancyLinkRetrievalCriteria())

    assert cursor == SiouxFacetCursor(
        facets=(("Software", "https://vacancy.sioux.eu/software", 2),),
        facet_index=0,
    )
    assert browser_access.open_calls == [
        (
            config.SIOUX_ENTRY_URL,
            (config.SIOUX_RESULTS_READY_SELECTOR,),
            (config.SIOUX_COOKIE_ACCEPT_SELECTOR,),
        )
    ]


def test_retrieve_vacancy_page_downloads_html_page() -> None:
    browser_access = FakeBrowserAccess(
        {},
        pages_by_url={
            "https://vacancy.sioux.eu/vacancies/one.html": "<html>Sioux vacancy</html>",
        },
    )
    retriever = SiouxVacancyLinkRetriever(browser_access=browser_access)

    page = retriever.retrieve_vacancy_page(
        "https://vacancy.sioux.eu/vacancies/one.html"
    )

    assert page == "<html>Sioux vacancy</html>"
    assert browser_access.download_calls == [
        "https://vacancy.sioux.eu/vacancies/one.html"
    ]


def test_retrieve_listing_batch_collects_paginated_facet_and_advances_cursor() -> None:
    first_facet_url = "https://vacancy.sioux.eu/software"
    second_page_url = "https://vacancy.sioux.eu/software?page=2"
    browser_access = FakeBrowserAccess(
        {
            first_facet_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/one.html"}),
                    FakeDOMElement(attributes={"href": "/vacancies/two.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [
                    FakeDOMElement(attributes={"href": second_page_url}),
                ],
            },
            second_page_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/three.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [],
            },
        }
    )
    retriever = SiouxVacancyLinkRetriever(browser_access=browser_access)
    cursor = SiouxFacetCursor(
        facets=(
            ("Software", first_facet_url, 3),
            ("Hardware", "https://vacancy.sioux.eu/hardware", 1),
        ),
        facet_index=0,
    )
    progress = vlr.VacancyLinkRetrievalProgress(
        retrieved_links=VacancyLinks(links=set()),
        criteria=VacancyLinkRetrievalCriteria(),
        iteration_index=0,
    )

    batch = retriever._retrieve_listing_batch(
        cursor=cursor,
        retrieval_progress=progress,
    )

    assert batch.retrieved_links == VacancyLinks(
        links={
            "https://vacancy.sioux.eu/vacancies/one.html",
            "https://vacancy.sioux.eu/vacancies/two.html",
            "https://vacancy.sioux.eu/vacancies/three.html",
        }
    )
    assert batch.next_cursor == SiouxFacetCursor(
        facets=cursor.facets,
        facet_index=1,
    )
    assert [call[0] for call in browser_access.open_calls] == [
        first_facet_url,
        second_page_url,
    ]


def test_retrieve_listing_batch_limits_extraction_to_remaining_overall_limit() -> None:
    first_facet_url = "https://vacancy.sioux.eu/software"
    second_page_url = "https://vacancy.sioux.eu/software?page=2"
    browser_access = FakeBrowserAccess(
        {
            first_facet_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/one.html"}),
                    FakeDOMElement(attributes={"href": "/vacancies/two.html"}),
                    FakeDOMElement(attributes={"href": "/vacancies/three.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [
                    FakeDOMElement(attributes={"href": second_page_url}),
                ],
            },
            second_page_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/four.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [],
            },
        }
    )
    retriever = SiouxVacancyLinkRetriever(browser_access=browser_access)
    cursor = SiouxFacetCursor(
        facets=(("Software", first_facet_url, 4),),
        facet_index=0,
    )
    progress = vlr.VacancyLinkRetrievalProgress(
        retrieved_links=VacancyLinks(links=set()),
        criteria=VacancyLinkRetrievalCriteria(links_limit=2),
        iteration_index=0,
    )

    batch = retriever._retrieve_listing_batch(
        cursor=cursor,
        retrieval_progress=progress,
    )

    assert batch.retrieved_links == VacancyLinks(
        links={
            "https://vacancy.sioux.eu/vacancies/one.html",
            "https://vacancy.sioux.eu/vacancies/two.html",
        }
    )
    assert batch.next_cursor is None
    assert [call[0] for call in browser_access.open_calls] == [first_facet_url]


def test_retrieve_listing_batch_skips_facet_when_expected_count_is_not_positive() -> None:
    first_facet_url = "https://vacancy.sioux.eu/software"
    browser_access = FakeBrowserAccess(
        {
            first_facet_url: {
                config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/one.html"}),
                ],
                config.SIOUX_NEXT_PAGE_SELECTOR: [],
            }
        }
    )
    retriever = SiouxVacancyLinkRetriever(browser_access=browser_access)
    cursor = SiouxFacetCursor(
        facets=(("Software", first_facet_url, 0),),
        facet_index=0,
    )
    progress = vlr.VacancyLinkRetrievalProgress(
        retrieved_links=VacancyLinks(links=set()),
        criteria=VacancyLinkRetrievalCriteria(),
        iteration_index=0,
    )

    batch = retriever._retrieve_listing_batch(
        cursor=cursor,
        retrieval_progress=progress,
    )

    assert batch.retrieved_links == VacancyLinks(links=set())
    assert batch.next_cursor is None
    assert browser_access.open_calls == []
