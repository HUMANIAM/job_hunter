from __future__ import annotations

from dataclasses import dataclass

from clients.sources.new_design import vacancy_link_retriever as vlr
from clients.sources.new_design.browser_access import BrowserAccess
from clients.sources.new_design.sioux import sioux_config as config
from clients.sources.new_design.sioux import sioux_dom_parser as dom_parser
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from infra.logging import log


@dataclass(frozen=True)
class SiouxFacetCursor:
    facets: tuple[dom_parser.DisciplineFacet, ...]
    facet_index: int


class SiouxVacancyLinkRetriever(vlr.VacancyLinkRetriever):
    def __init__(
        self,
        browser_access: BrowserAccess,
    ) -> None:
        self._browser_access = browser_access

    def _get_initial_cursor(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria,
    ) -> SiouxFacetCursor | None:
        # TODO: Apply filters from the criteria (e.g. country filter may require selecting a different entry page)
        self._open_listing_page(config.SIOUX_ENTRY_URL)

        facet_elements = self._browser_access.find_elements(
            config.SIOUX_DISCIPLINE_FACET_SELECTOR
        )

        facets = tuple(
            dom_parser.extract_discipline_facets(
                facet_elements,
                entry_url=config.SIOUX_ENTRY_URL,
            )
        )

        log(f"SiouxVacancyLinkRetriever: collected {len(facets)} discipline facets")

        if not facets:
            return None

        return SiouxFacetCursor(facets=facets, facet_index=0)


    def _retrieve_listing_batch(
        self,
        cursor: SiouxFacetCursor,
        retrieval_progress: vlr.VacancyLinkRetrievalProgress,
    ) -> vlr.VacancyLinkBatch:
        """Retrieve one complete Sioux discipline facet.

        The shared retriever loop treats this method as one batch step. For
        Sioux, a batch is a whole facet, including all pagination inside that
        facet. This method collects the current facet links and returns the
        next cursor pointing at the next facet, or None when all facets are
        complete.
        """
        facet_name, facet_url, expected_count = cursor.facets[cursor.facet_index]
        if expected_count <= 0:
            log(
                f"facet '{facet_name}': expected count is {expected_count}, "
                "skipping facet"
            )
            return vlr.VacancyLinkBatch(
                retrieved_links=VacancyLinks(links=set()),
                next_cursor=self._create_next_cursor(cursor),
            )

        links_limit = self._remaining_links_limit(retrieval_progress)

        retrieved_links = self._collect_facet_links(
            facet_name=facet_name,
            facet_url=facet_url,
            expected_count=expected_count,
            links_limit=links_limit,
        )

        return vlr.VacancyLinkBatch(
            retrieved_links=retrieved_links,
            next_cursor=self._create_next_cursor(cursor),
        )

    def _collect_facet_links(
        self,
        *,
        facet_name: str,
        facet_url: str,
        expected_count: int,
        links_limit: int,
    ) -> VacancyLinks:

        log(f"facet '{facet_name}': opening facet page")

        collected_links: set[str] = set()
        visited_page_urls: set[str] = set()
        page_url = facet_url
        page_index = 1
        remaining_links_to_retrieve = links_limit

        while remaining_links_to_retrieve > 0:
            self._open_listing_page(page_url)
            current_url = self._browser_access.current_url()
            if current_url in visited_page_urls:
                log(f"facet '{facet_name}': detected repeated page url, stopping")
                break

            visited_page_urls.add(current_url)
            page_links = self._extract_current_page_vacancy_links(
                links_limit=remaining_links_to_retrieve
            )
            log(
                f"facet '{facet_name}' page {page_index}: "
                f"collected {len(page_links.links)} links from current page"
            )

            collected_links.update(page_links.links)

            remaining_links_to_retrieve = max(
                links_limit - len(collected_links),
                0,
            )
            if remaining_links_to_retrieve <= 0:
                log(f"facet '{facet_name}': no remaining links to retrieve")
                break

            next_page_url = self._extract_next_page_url()
            if next_page_url is None:
                log(f"facet '{facet_name}': no next page link")
                break

            if next_page_url in visited_page_urls:
                log(f"facet '{facet_name}': next page url already visited, stopping")
                break

            log(f"facet '{facet_name}': following next page -> {next_page_url}")
            page_url = next_page_url
            page_index += 1

        log(
            f"facet '{facet_name}': collected {len(collected_links)} unique links "
            f"(sidebar expected count={expected_count})"
        )

        return VacancyLinks(links=collected_links)


    def _open_listing_page(self, url: str) -> None:
        self._browser_access.open_url(
            url,
            wait_for_selectors=(config.SIOUX_RESULTS_READY_SELECTOR,),
            click_if_visible_selectors=(config.SIOUX_COOKIE_ACCEPT_SELECTOR,),
        )

        log(f"current page url: {self._browser_access.current_url()}")


    def _extract_current_page_vacancy_links(
        self,
        *,
        links_limit: int,
    ) -> VacancyLinks:
        vacancy_elements = self._browser_access.find_elements(
            config.SIOUX_RESULTS_READY_SELECTOR
        )

        log(f"found {len(vacancy_elements)} vacancy cards")

        return dom_parser.extract_vacancy_links(
            vacancy_elements,
            entry_url=config.SIOUX_ENTRY_URL,
            job_url_pattern=config.SIOUX_JOB_URL_RE,
            links_limit=links_limit,
        )

    def _extract_next_page_url(self) -> str | None:
        next_page_elements = self._browser_access.find_elements(
            config.SIOUX_NEXT_PAGE_SELECTOR
        )
        return dom_parser.extract_next_page_url(
            next_page_elements,
            entry_url=config.SIOUX_ENTRY_URL,
        )

    def _create_next_cursor(
        self,
        cursor: SiouxFacetCursor,
    ) -> SiouxFacetCursor | None:
        next_facet_index = cursor.facet_index + 1
        if next_facet_index >= len(cursor.facets):
            return None

        return SiouxFacetCursor(
            facets=cursor.facets,
            facet_index=next_facet_index,
        )
