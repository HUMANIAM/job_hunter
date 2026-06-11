from __future__ import annotations

from contextlib import ExitStack, contextmanager
from typing import Callable, Iterator

from clients.clients import Client
from clients.sources.new_design.philips.philips_vacancy_source_provider import (
    create_philips_vacancy_source_provider,
)
from clients.sources.new_design.playwright_browser_access import (
    create_playwright_browser_access,
)
from clients.sources.new_design.requests_http_access import RequestsHttpAccess
from clients.sources.new_design.sioux.sioux_vacancy_source_provider import (
    create_sioux_vacancy_source_provider,
)
from clients.sources.new_design.vacancy_source import VacancySource

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


@contextmanager
def create_vacancy_source_registry() -> Iterator[VacancySourceRegistry]:
    """Create a vacancy source registry and close provider resources after use."""
    with ExitStack() as stack:
        philips_http = stack.enter_context(RequestsHttpAccess())
        sioux_browser_access = stack.enter_context(create_playwright_browser_access())

        yield VacancySourceRegistry(
            providers={
                Client.PHILIPS: create_philips_vacancy_source_provider(
                    http_access=philips_http,
                ),
                Client.SIOUX: create_sioux_vacancy_source_provider(
                    browser_access=sioux_browser_access,
                ),
            }
        )
