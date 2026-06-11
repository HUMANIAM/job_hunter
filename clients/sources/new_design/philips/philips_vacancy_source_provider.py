from typing import Callable

from clients.sources.new_design import http_access as http
from clients.sources.new_design.philips.philips_vacancy_link_retriever import (
    PhilipsVacancyLinkRetriever,
)
from clients.sources.new_design.philips.philips_vacancy_source import (
    PhilipsVacancySource,
)


def create_philips_vacancy_source(
    http_access: http.HttpAccess,
) -> PhilipsVacancySource:
    retriever = PhilipsVacancyLinkRetriever(http_access=http_access)
    return PhilipsVacancySource(retriever=retriever)


def create_philips_vacancy_source_provider(
    http_access: http.HttpAccess,
) -> Callable[[], PhilipsVacancySource]:
    def provide_vacancy_source() -> PhilipsVacancySource:
        return create_philips_vacancy_source(http_access=http_access)

    return provide_vacancy_source
