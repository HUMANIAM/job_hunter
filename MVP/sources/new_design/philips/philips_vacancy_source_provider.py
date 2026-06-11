from typing import Callable

from MVP.sources.new_design.retrieval_access import http_access as http
from MVP.sources.new_design.philips.philips_vacancy_retriever import (
    PhilipsVacancyRetriever,
)
from MVP.sources.new_design.philips.philips_vacancy_source import (
    PhilipsVacancySource,
)


def create_philips_vacancy_source(
    http_access: http.HttpAccess,
) -> PhilipsVacancySource:
    retriever = PhilipsVacancyRetriever(http_access=http_access)
    return PhilipsVacancySource(retriever=retriever)


def create_philips_vacancy_source_provider(
    http_access: http.HttpAccess,
) -> Callable[[], PhilipsVacancySource]:
    def provide_vacancy_source() -> PhilipsVacancySource:
        return create_philips_vacancy_source(http_access=http_access)

    return provide_vacancy_source
