from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List

from clients.base import BaseClientAdapter
from infra.logging import log


@dataclass(frozen=True)
class APIPageResult:
    job_links: set[str]
    next_request_state: Any | None
    expected_total: int | None = None
    is_last_page: bool = False


class APIListingAdapter(BaseClientAdapter, ABC):
    def collect_job_links(
        self,
        *,
        job_limit: int,
    ) -> List[str]:
        collected_links: set[str] = set()
        seen_request_states: set[str] = set()
        request_state = self._get_initial_request_state()
        page_index = 1
        expected_total: int | None = None

        while request_state is not None:
            state_key = self._get_request_state_key(request_state)
            if state_key in seen_request_states:
                log(f"{self.__class__.__name__}: repeated request state, stopping")
                break
            seen_request_states.add(state_key)

            response = self._fetch_listing_response(request_state)
            page_result = self._parse_listing_response(
                response,
                request_state=request_state,
                page_index=page_index,
                remaining_job_budget=job_limit - len(collected_links),
            )

            before = len(collected_links)
            collected_links.update(page_result.job_links)
            after = len(collected_links)

            log(
                f"{self.__class__.__name__} page {page_index}: "
                f"added {after - before} new links | cumulative={after}"
            )

            if expected_total is None and page_result.expected_total is not None:
                expected_total = page_result.expected_total
                log(f"{self.__class__.__name__}: expected_total={expected_total}")

            if after >= job_limit:
                log(f"{self.__class__.__name__}: reached job limit, stopping")
                break

            if expected_total is not None and after >= expected_total:
                log(f"{self.__class__.__name__}: reached expected total, stopping")
                break

            if page_result.is_last_page:
                log(f"{self.__class__.__name__}: api reported last page")
                break

            request_state = page_result.next_request_state
            page_index += 1

        return sorted(collected_links)

    @abstractmethod
    def _get_initial_request_state(self) -> Any:
        """Return the initial request state for the first API call."""
        raise NotImplementedError

    @abstractmethod
    def _fetch_listing_response(self, request_state: Any) -> Any:
        """Execute one listing request and return the raw response payload."""
        raise NotImplementedError

    @abstractmethod
    def _parse_listing_response(
        self,
        response: Any,
        *,
        request_state: Any,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        """Extract links and pagination info from one raw API response."""
        raise NotImplementedError

    def _get_request_state_key(self, request_state: Any) -> str:
        """Return a stable dedupe key for loop detection."""
        return repr(request_state)