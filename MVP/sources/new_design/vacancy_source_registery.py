from __future__ import annotations

from contextlib import ExitStack, contextmanager
from functools import partial
from typing import Callable, Iterator

from MVP.clients import Client
from MVP.sources.new_design.philips.philips_vacancy_source_provider import (
    create_philips_vacancy_source,
)
from MVP.sources.new_design.retrieval_access.playwright_browser_access import (
    create_playwright_browser_access,
)
from MVP.sources.new_design.retrieval_access.requests_http_access import RequestsHttpAccess
from MVP.sources.new_design.sioux.sioux_vacancy_source_provider import (
    create_sioux_vacancy_source,
)
from MVP.sources.new_design.vacancy_source import VacancySource

VacancySourceProvider = Callable[[], VacancySource]


class VacancySourceRegistry:
    """Multiton registry for vacancy sources created during program startup."""

    def __init__(
        self,
        *,
        providers: dict[Client, VacancySourceProvider],
    ) -> None:
        self._providers = providers
        self._sources: dict[Client, VacancySource] = {}

    def get_vacancy_source(self, client: Client) -> VacancySource:
        if client not in self._sources:
            self._sources[client] = self._create_vacancy_source(client)

        return self._sources[client]

    def _create_vacancy_source(self, client: Client) -> VacancySource:
        try:
            provider = self._providers[client]
        except KeyError as exc:
            raise ValueError(
                f"No vacancy source registered for client: {client.value}"
            ) from exc

        return provider()


def _create_philips_source(stack: ExitStack) -> VacancySource:
    philips_http = stack.enter_context(RequestsHttpAccess())
    return create_philips_vacancy_source(http_access=philips_http)


def _create_sioux_source(stack: ExitStack) -> VacancySource:
    sioux_browser_access = stack.enter_context(create_playwright_browser_access())
    return create_sioux_vacancy_source(browser_access=sioux_browser_access)


@contextmanager
def create_vacancy_source_registry() -> Iterator[VacancySourceRegistry]:
    """Create a vacancy source registry and close provider resources after use."""
    with ExitStack() as stack:
        yield VacancySourceRegistry(
            providers={
                Client.PHILIPS: partial(_create_philips_source, stack),
                Client.SIOUX: partial(_create_sioux_source, stack),
            }
        )
