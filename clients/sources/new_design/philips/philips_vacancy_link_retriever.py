from __future__ import annotations

from dataclasses import dataclass

from clients.sources.new_design import http_access as http
from clients.sources.new_design import vacancy_link_retriever as vlr
from clients.sources.new_design.philips import philips_config as config
from clients.sources.new_design.philips import philips_request_factory as request_factory
from clients.sources.new_design.philips import philips_response_parser as response_parser
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria
from infra.logging import log

@dataclass(frozen=True)
class PhilipsPageCursor:
    offset: int
    country_facet_id: str


class PhilipsVacancyLinkRetriever(vlr.VacancyLinkRetriever):
    def __init__(
        self,
        http_access: http.HttpAccess,
    ) -> None:
        self._http_access = http_access

    def retrieve_vacancy_page(self, vacancy_url: str) -> str:
        response = self._http_access.get(
            http.HttpRequest(
                url=vacancy_url,
                headers={
                    "Accept": "text/html",
                    "Accept-Language": config.DEFAULT_LOCALE,
                },
                timeout_seconds=config.REQUEST_TIMEOUT_SECONDS,
            )
        )

        if not isinstance(response.content, str):
            raise TypeError("Expected text content when retrieving Philips vacancy page")

        return response.content

    def _get_initial_cursor(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria,
    ) -> PhilipsPageCursor | None:
        """Resolve the configured country facet and start listing pagination."""

        country = self._get_country(criteria)
        cursor = PhilipsPageCursor(offset=0, country_facet_id="")
        response = self._make_post_listing_request(cursor)

        country_facet_id = response_parser.discover_country_facet_id(
            response.content,
            country=country,
        )

        if not country_facet_id:
            log(
                f"PhilipsVacancyLinkRetriever: "
                f"{country} facet not found"
            )
            return None

        return PhilipsPageCursor(offset=0, country_facet_id=country_facet_id)


    def _retrieve_listing_batch(
        self,
        cursor: PhilipsPageCursor,
        retrieval_progress: vlr.VacancyLinkRetrievalProgress,
    ) -> vlr.VacancyLinkBatch:
        """Retrieve one Philips listing page and return its links plus next cursor."""

        response = self._make_post_listing_request(cursor)

        raw_job_postings = response_parser.get_job_postings(response.content)
        links_limit = self._remaining_links_limit(retrieval_progress)
        retrieved_links = response_parser.extract_vacancy_links(
            raw_job_postings,
            links_limit=links_limit,
        )

        batch_size = len(raw_job_postings)
        is_complete = self._is_complete(batch_size)
        next_cursor = self._create_next_cursor(
            is_complete=is_complete,
            batch_size=batch_size,
            current_cursor=cursor,
        )

        return vlr.VacancyLinkBatch(
            retrieved_links=retrieved_links,
            next_cursor=next_cursor,
        )


    def _make_post_listing_request(self, cursor: PhilipsPageCursor) -> http.HttpResponse:
        """Build and send the Philips listing request for the cursor."""

        request = request_factory.build_listing_request(
            offset=cursor.offset,
            country_facet_id=cursor.country_facet_id or None,
        )
        return self._http_access.post(request)


    def _get_country(self, criteria: VacancyLinkRetrievalCriteria) -> str:
        """Return the requested country or the Philips default country."""

        return criteria.country or config.DEFAULT_COUNTRY


    def _is_complete(self, batch_size: int) -> bool:
        """Return whether the current Philips listing batch exhausts pagination."""

        return batch_size == 0 or batch_size < config.PHILIPS_PAGE_SIZE


    def _create_next_cursor(
        self,
        *,
        is_complete: bool,
        batch_size: int,
        current_cursor: PhilipsPageCursor,
    ) -> PhilipsPageCursor | None:
        """Create the next Philips cursor unless pagination is complete."""

        if is_complete:
            return None

        return PhilipsPageCursor(
            offset=current_cursor.offset + batch_size,
            country_facet_id=current_cursor.country_facet_id,
        )
