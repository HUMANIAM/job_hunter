from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import sys

from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from infra.logging import log


@dataclass
class VacancyLinkRetrievalProgress:
    retrieved_links: VacancyLinks
    criteria: VacancyLinkRetrievalCriteria
    iteration_index: int


@dataclass(frozen=True)
class VacancyLinkBatch:
    retrieved_links: VacancyLinks
    next_cursor: object | None


class VacancyRetriever(ABC):
    def retrieve_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        """
        Retrieve links to job vacancies.
        Args:
            criteria: optional criteria for retrieving vacancy links.
        Returns:
            A VacancyLinks object containing the retrieved links.
        """
        criteria = criteria or VacancyLinkRetrievalCriteria()
        progress = VacancyLinkRetrievalProgress(
            retrieved_links=VacancyLinks(links=set()),
            criteria=criteria,
            iteration_index=0,
        )

        cursor = self._get_initial_cursor(criteria=criteria)
        while cursor is not None:
            batch = self._retrieve_listing_batch(
                cursor=cursor,
                retrieval_progress=progress,
            )

            log(
                "vacancy link retrieval: retrieved batch "
                f"batch_size={len(batch.retrieved_links.links)} "
                f"total_links={len(progress.retrieved_links.links)} "
                f"iteration={progress.iteration_index}"
            )

            progress.retrieved_links.links.update(batch.retrieved_links.links)

            if self._stop_retrieval(progress=progress, batch=batch):
                break

            cursor = batch.next_cursor
            progress.iteration_index += 1

        links_limit = progress.criteria.links_limit
        if links_limit is None:
            return progress.retrieved_links

        progress.retrieved_links.links = set(
            list(progress.retrieved_links.links)[:links_limit]
        )

        return progress.retrieved_links

    @abstractmethod
    def retrieve_vacancy_page(self, vacancy_url: str) -> str:
        """
        Retrieve the raw page content for a vacancy URL.
        Args:
            vacancy_url: The vacancy URL to retrieve.
        Returns:
            The raw vacancy page content.
        """
        pass

    @abstractmethod
    def _get_initial_cursor(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria,
    ) -> object | None:
        """
        Get the initial cursor for vacancy link retrieval.
        Returns:
            The initial cursor object, or None if no cursor is needed.
        """
        pass

    @abstractmethod
    def _retrieve_listing_batch(
        self,
        cursor: object | None,
        retrieval_progress: VacancyLinkRetrievalProgress,
    ) -> VacancyLinkBatch:
        """
        Retrieve the next step of vacancy links using the provided cursor.
        Args:
            cursor: The cursor object obtained from the previous retrieval step, or None for the initial step.
        Returns:
            A VacancyLinkBatch object containing the retrieved links and the next cursor.
        """
        pass

    def _stop_retrieval(
        self,
        progress: VacancyLinkRetrievalProgress,
        batch: VacancyLinkBatch,
    ) -> bool:
        if batch.next_cursor is None:
            return True

        links_len = len(progress.retrieved_links.links)

        links_limit = progress.criteria.links_limit
        if links_limit is not None and links_len >= links_limit:
            log(
                "vacancy link retrieval: reached links limit "
                f"links_limit={links_limit} "
                f"retrieved_links={links_len}"
            )
            return True

        return False

    def _remaining_links_limit(
        self,
        retrieval_progress: VacancyLinkRetrievalProgress,
    ) -> int:
        links_limit = retrieval_progress.criteria.links_limit
        if links_limit is None:
            return sys.maxsize

        return max(
            links_limit - len(retrieval_progress.retrieved_links.links),
            0,
        )
