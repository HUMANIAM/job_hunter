from __future__ import annotations

from abc import ABC, abstractmethod

from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks


class VacancySource(ABC):
    @abstractmethod
    def get_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        """
        Get links to job vacancies from the source.
        Args:
            criteria: optional criteria for retrieving vacancy links.
        Returns:
            A VacancyLinks object containing the retrieved links.
        """
        pass

    @abstractmethod
    def get_vacancy_page(self, vacancy_url: str) -> str:
        """
        Get the raw vacancy page content.
        Args:
            vacancy_url: URL of the vacancy page to retrieve.
        Returns:
            The raw vacancy page HTML.
        """
        pass
