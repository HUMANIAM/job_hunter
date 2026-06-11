from __future__ import annotations

import pytest

from clients.clients import Client
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from clients.sources.new_design.vacancy_source import VacancySource
from clients.sources.new_design.vacancy_source_registery import (
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


def test_registry_provider_registers_philips_source() -> None:
    with create_vacancy_source_registry() as registry:
        source = registry.get_vacancy_source(Client.PHILIPS)

    assert isinstance(source, VacancySource)
