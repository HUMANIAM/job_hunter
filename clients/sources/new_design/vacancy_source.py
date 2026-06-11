from __future__ import annotations

from abc import ABC, abstractmethod

from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks


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
