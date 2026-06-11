from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pytest

from MVP.clients import Client
from MVP.sources.new_design import vacancy_source_registery as registry_module
from MVP.sources.new_design.retrieval_access.browser_access import (
    BrowserAccess,
    DOMElement,
    Selector,
    SelectorList,
)
from MVP.sources.new_design.sioux import sioux_config as sioux_config
from MVP.sources.new_design.tests.data.dom import FakeDOMElement
from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from MVP.sources.new_design.vacancy_source import VacancySource
from MVP.sources.new_design.vacancy_source_registery import (
    VacancySourceRegistry,
    create_vacancy_source_registry,
)


class FakeVacancySource(VacancySource):
    def get_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        return VacancyLinks(links=set())

    def get_vacancy_page(self, vacancy_url: str) -> str:
        return f"<html>{vacancy_url}</html>"


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


@contextmanager
def fake_playwright_browser_access_create() -> Iterator[BrowserAccess]:
    facet_url = "https://vacancy.sioux.eu/software"
    yield FakeBrowserAccess(
        {
            sioux_config.SIOUX_ENTRY_URL: {
                sioux_config.SIOUX_DISCIPLINE_FACET_SELECTOR: [
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
                sioux_config.SIOUX_RESULTS_READY_SELECTOR: [
                    FakeDOMElement(attributes={"href": "/vacancies/one.html"}),
                ],
                sioux_config.SIOUX_NEXT_PAGE_SELECTOR: [],
            },
        }
    )


def test_registry_reuses_source_instance_for_same_client() -> None:
    create_count = 0

    def provide_source() -> VacancySource:
        nonlocal create_count
        create_count += 1
        return FakeVacancySource()

    registry = VacancySourceRegistry(providers={Client.PHILIPS: provide_source})

    first_source = registry.get_vacancy_source(Client.PHILIPS)
    second_source = registry.get_vacancy_source(Client.PHILIPS)

    assert first_source is second_source
    assert create_count == 1


def test_registry_raises_for_unregistered_client() -> None:
    registry = VacancySourceRegistry(providers={})

    with pytest.raises(ValueError, match="No vacancy source registered"):
        registry.get_vacancy_source(Client.PHILIPS)


def test_registry_provider_registers_philips_source(monkeypatch) -> None:
    @contextmanager
    def fail_playwright_browser_access_create() -> Iterator[BrowserAccess]:
        raise AssertionError("Philips source creation should not start Playwright")
        yield

    monkeypatch.setattr(
        registry_module,
        "create_playwright_browser_access",
        fail_playwright_browser_access_create,
    )
    with create_vacancy_source_registry() as registry:
        source = registry.get_vacancy_source(Client.PHILIPS)

    assert isinstance(source, VacancySource)


def test_registry_provider_registers_sioux_source(monkeypatch) -> None:
    monkeypatch.setattr(
        registry_module,
        "create_playwright_browser_access",
        fake_playwright_browser_access_create,
    )

    with create_vacancy_source_registry() as registry:
        source = registry.get_vacancy_source(Client.SIOUX)

    assert isinstance(source, VacancySource)
