from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from clients.sources.api_listing_adapter import APIListingAdapter, APIPageResult
from infra.logging import log


API_URL = "https://jobs.cpp.canon/services/recruiting/v1/jobs"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class CanonListingFilters:
    locale: str = "en_GB"
    location: str = "Venlo"
    job_type: str = "Professional"
    options_facets_job_type: str = "Professional"


@dataclass(frozen=True)
class CanonPageState:
    page_number: int


class CanonAPIListingAdapter(APIListingAdapter):
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        filters: CanonListingFilters | None = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        self._session = session or requests.Session()
        self._filters = filters or CanonListingFilters()
        self._max_attempts = max_attempts

    def _get_max_attempts(self) -> int:
        return self._max_attempts

    def _get_initial_request_state(self) -> CanonPageState:
        return CanonPageState(page_number=0)

    def _fetch_listing_response(
        self,
        request_state: CanonPageState,
    ) -> dict[str, Any]:
        response = self._session.post(
            API_URL,
            headers=self._build_headers(request_state.page_number),
            json=self._build_payload(request_state.page_number),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            log(
                f"{self.__class__.__name__}: request failed "
                f"status={response.status_code} "
                f"page={request_state.page_number} "
                f"url={response.url}"
            )
            raise

        return response.json()

    def _parse_listing_response(
        self,
        response: dict[str, Any],
        *,
        request_state: CanonPageState,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        job_links = self._extract_job_urls(
            response_body=response,
            limit=remaining_job_budget,
        )

        raw_total = response.get("totalJobs")
        expected_total = raw_total if isinstance(raw_total, int) and raw_total > 0 else None

        has_results = bool(job_links)
        next_request_state = (
            CanonPageState(page_number=request_state.page_number + 1)
            if has_results
            else None
        )

        return APIPageResult(
            job_links=job_links,
            next_request_state=next_request_state,
            expected_total=expected_total,
            is_last_page=not has_results,
        )

    def _build_headers(self, page_number: int) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Referer": self._build_page_url(page_number),
        }

    def _build_payload(self, page_number: int) -> dict[str, Any]:
        return {
            "locale": self._filters.locale,
            "pageNumber": page_number,
            "sortBy": "",
            "keywords": "",
            "location": "",
            "facetFilters": {
                "jobType": [self._filters.job_type],
                "sfstd_jobLocation_obj": [self._filters.location],
            },
            "brand": "",
            "skills": [],
            "categoryId": 0,
            "alertId": "",
            "rcmCandidateId": "",
        }

    def _build_page_url(self, page_number: int) -> str:
        facet_filters = quote(
            (
                f'{{"jobType":["{self._filters.job_type}"],'
                f'"sfstd_jobLocation_obj":["{self._filters.location}"]}}'
            )
        )

        return (
            "https://jobs.cpp.canon/search/"
            f"?locale={self._filters.locale}"
            f"&optionsFacetsDD_customfield3={self._filters.options_facets_job_type}"
            "&searchResultView=LIST"
            "&markerViewed="
            "&carouselIndex="
            f"&pageNumber={page_number}"
            f"&facetFilters={facet_filters}"
        )

    def _extract_job_urls(
        self,
        *,
        response_body: dict[str, Any],
        limit: int,
    ) -> set[str]:
        urls: set[str] = set()

        if limit <= 0:
            return urls

        for item in response_body.get("jobSearchResult") or []:
            item_response = item.get("response") or {}
            url_title = item_response.get("urlTitle") or item_response.get("unifiedUrlTitle")
            job_id = item_response.get("id")
            if not url_title or not job_id:
                continue

            urls.add(
                f"https://jobs.cpp.canon/job/{url_title}/{job_id}-en_GB"
            )
            if len(urls) >= limit:
                break

        return urls