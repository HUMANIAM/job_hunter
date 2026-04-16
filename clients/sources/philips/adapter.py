from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from clients.sources.api_listing_adapter import APIListingAdapter, APIPageResult
from infra.logging import log


ENTRY_URL = "https://philips.wd3.myworkdayjobs.com/nl-nl/jobs-and-careers"
API_URL = "https://philips.wd3.myworkdayjobs.com/wday/cxs/philips/jobs-and-careers/jobs"
ORIGIN_URL = "https://philips.wd3.myworkdayjobs.com"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_ATTEMPTS = 1
PHILIPS_PAGE_SIZE = 20
JOB_PATH_PREFIX = "/job/"


@dataclass(frozen=True)
class PhilipsListingFilters:
    locale: str = "nl-NL"
    country_descriptor: str = "Netherlands"
    location_group_facet_parameter: str = "locationMainGroup"
    location_facet_parameter: str = "locationHierarchy1"


@dataclass(frozen=True)
class PhilipsPageState:
    offset: int
    country_facet_id: str


class PhilipsAPIListingAdapter(APIListingAdapter):
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        filters: PhilipsListingFilters | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._session = session or requests.Session()
        self._filters = filters or PhilipsListingFilters()
        self._max_attempts = max_attempts

    def _get_max_attempts(self) -> int:
        return self._max_attempts

    def _get_initial_request_state(self) -> PhilipsPageState | None:
        country_facet_id = self._discover_country_facet_id()
        if not country_facet_id:
            log(
                f"{self.__class__.__name__}: "
                f"{self._filters.country_descriptor} facet not found"
            )
            return None

        return PhilipsPageState(offset=0, country_facet_id=country_facet_id)

    def _fetch_listing_response(
        self,
        request_state: PhilipsPageState,
    ) -> dict[str, Any]:
        return self._post_api_request(
            offset=request_state.offset,
            country_facet_id=request_state.country_facet_id,
        )

    def _parse_listing_response(
        self,
        response: dict[str, Any],
        *,
        request_state: PhilipsPageState,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        raw_job_postings = self._get_job_postings(response_body=response)
        filtered_job_postings = self._filter_job_postings(
            job_postings=raw_job_postings,
        )
        job_links = self._extract_job_urls(
            job_postings=filtered_job_postings,
            limit=remaining_job_budget,
        )

        raw_total = response.get("total")
        expected_total = raw_total if isinstance(raw_total, int) and raw_total > 0 else None

        batch_size = len(raw_job_postings)
        is_last_page = batch_size == 0 or batch_size < PHILIPS_PAGE_SIZE
        next_request_state = (
            None
            if is_last_page
            else PhilipsPageState(
                offset=request_state.offset + batch_size,
                country_facet_id=request_state.country_facet_id,
            )
        )

        return APIPageResult(
            job_links=job_links,
            next_request_state=next_request_state,
            expected_total=expected_total,
            is_last_page=is_last_page,
        )

    def _post_api_request(
        self,
        *,
        offset: int,
        country_facet_id: str | None,
    ) -> dict[str, Any]:
        response = self._session.post(
            API_URL,
            headers=self._build_headers(),
            json=self._build_payload(
                offset=offset,
                country_facet_id=country_facet_id,
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            log(
                f"{self.__class__.__name__}: request failed "
                f"status={response.status_code} "
                f"offset={offset} "
                f"url={response.url}"
            )
            raise

        return response.json()

    def _build_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Accept-Language": self._filters.locale,
            "Content-Type": "application/json",
            "Origin": ORIGIN_URL,
            "Referer": self._build_page_url(),
        }

    def _build_payload(
        self,
        *,
        offset: int,
        country_facet_id: str | None,
    ) -> dict[str, Any]:
        applied_facets = (
            {self._filters.location_facet_parameter: [country_facet_id]}
            if country_facet_id
            else {}
        )

        return {
            "appliedFacets": applied_facets,
            "limit": PHILIPS_PAGE_SIZE,
            "offset": offset,
            "searchText": "",
        }

    def _build_page_url(self) -> str:
        return ENTRY_URL

    def _discover_country_facet_id(self) -> str | None:
        response = self._post_api_request(offset=0, country_facet_id=None)
        facets = response.get("facets") or []

        for facet in facets:
            if (
                facet.get("facetParameter")
                != self._filters.location_group_facet_parameter
            ):
                continue

            for group in facet.get("values") or []:
                if (
                    group.get("facetParameter")
                    != self._filters.location_facet_parameter
                ):
                    continue

                for value in group.get("values") or []:
                    descriptor = value.get("descriptor")
                    if not isinstance(descriptor, str):
                        continue

                    if descriptor.strip() != self._filters.country_descriptor:
                        continue

                    facet_id = value.get("id")
                    if facet_id:
                        return str(facet_id)

        return None

    def _get_job_postings(
        self,
        *,
        response_body: dict[str, Any],
    ) -> list[dict[str, Any]]:
        job_postings = response_body.get("jobPostings") or []
        return [job_posting for job_posting in job_postings if isinstance(job_posting, dict)]

    def _filter_job_postings(
        self,
        *,
        job_postings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        filtered_job_postings: list[dict[str, Any]] = []

        for job_posting in job_postings:
            external_path = job_posting.get("externalPath")
            if not isinstance(external_path, str):
                continue

            if not external_path.startswith(JOB_PATH_PREFIX):
                continue

            filtered_job_postings.append(job_posting)

        return filtered_job_postings

    def _extract_job_urls(
        self,
        *,
        job_postings: list[dict[str, Any]],
        limit: int,
    ) -> set[str]:
        urls: set[str] = set()

        if limit <= 0:
            return urls

        for job_posting in job_postings:
            external_path = job_posting.get("externalPath")
            if not isinstance(external_path, str):
                continue

            urls.add(self._build_job_url(external_path))
            if len(urls) >= limit:
                break

        return urls

    def _build_job_url(self, external_path: str) -> str:
        normalized_path = (
            external_path if external_path.startswith("/") else f"/{external_path}"
        )
        return f"{ENTRY_URL}{normalized_path}"


PhilipsClientAdapter = PhilipsAPIListingAdapter
