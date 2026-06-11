from __future__ import annotations

from typing import Callable

from MVP.sources.new_design.retrieval_access.browser_access import BrowserAccess
from MVP.sources.new_design.sioux.sioux_vacancy_retriever import (
    SiouxVacancyRetriever,
)
from MVP.sources.new_design.sioux.sioux_vacancy_source import SiouxVacancySource


def create_sioux_vacancy_source(
    browser_access: BrowserAccess,
) -> SiouxVacancySource:
    retriever = SiouxVacancyRetriever(browser_access=browser_access)
    return SiouxVacancySource(retriever=retriever)


def create_sioux_vacancy_source_provider(
    browser_access: BrowserAccess,
) -> Callable[[], SiouxVacancySource]:
    def provide_vacancy_source() -> SiouxVacancySource:
        return create_sioux_vacancy_source(browser_access=browser_access)

    return provide_vacancy_source
