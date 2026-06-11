from __future__ import annotations

from MVP.sources.new_design import vacancy_retriever as vr
from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from MVP.sources.new_design.vacancy_source import VacancySource


class SiouxVacancySource(VacancySource):
    def __init__(self, retriever: vr.VacancyRetriever) -> None:
        self._retriever = retriever

    def get_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        return self._retriever.retrieve_vacancy_links(criteria=criteria)

    def get_vacancy_page(self, vacancy_url: str) -> str:
        return self._retriever.retrieve_vacancy_page(vacancy_url)
