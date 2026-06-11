from __future__ import annotations

from clients.sources.new_design import vacancy_link_retriever as vlr
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from clients.sources.new_design.vacancy_source import VacancySource


class SiouxVacancySource(VacancySource):
    def __init__(self, retriever: vlr.VacancyLinkRetriever) -> None:
        self._retriever = retriever

    def get_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        return self._retriever.retrieve_vacancy_links(criteria=criteria)
