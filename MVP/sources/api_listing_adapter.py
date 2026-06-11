from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from MVP.base import BaseClientAdapter
from infra.logging import log
from shared.utils import _max


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
    ) -> list[str]:
        accumulated_links: set[str] = set()
        best_total_links_count: int | None = None
        max_attempts = self._get_max_attempts()
        class_name = self.__class__.__name__

        for attempt_index in range(1, max_attempts + 1):
            log(f"{class_name}: attempt {attempt_index}/{max_attempts}")

            attempt_links, expected_total_links_count = self._collect_job_links_once(
                job_limit=job_limit,
            )
            best_total_links_count = _max(
                best_total_links_count,
                expected_total_links_count,
            )

            accumulated_links.update(attempt_links)

            if (
                best_total_links_count is not None
                and len(accumulated_links) >= best_total_links_count
            ):
                log(
                    f"{class_name}: reached expected total {best_total_links_count}"
                    f" across {attempt_index} attempts, stopping"
                )
                break

            if len(accumulated_links) >= job_limit:
                log(
                    f"{class_name}: reached job limit {job_limit} "
                    f"across {attempt_index} attempts, stopping"
                )
                break

        return sorted(accumulated_links)[:job_limit]

    def _collect_job_links_once(
        self,
        *,
        job_limit: int,
    ) -> tuple[set[str], int | None]:
        class_name = self.__class__.__name__
        collected_links: set[str] = set()
        seen_request_states: set[str] = set()
        request_state = self._get_initial_request_state()
        page_index = 1
        expected_total: int | None = None

        while request_state is not None:
            if len(collected_links) >= job_limit:
                log(f"{class_name}: reached job limit, stopping")
                break

            state_key = self._get_request_state_key(request_state)
            if state_key in seen_request_states:
                log(f"{class_name}: repeated request state, stopping")
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
                f"{class_name} page {page_index}: "
                f"added {after - before} new links | cumulative={after}"
            )

            if after == before:
                log(f"{class_name}: page yielded no new links, stopping")
                break

            if expected_total is None and page_result.expected_total is not None:
                expected_total = page_result.expected_total
                log(f"{class_name}: expected_total={expected_total}")

            if after >= job_limit:
                log(f"{class_name}: reached job limit, stopping")
                break

            if expected_total is not None and after >= expected_total:
                log(f"{class_name}: reached expected total, stopping")
                break

            if page_result.is_last_page:
                log(f"{class_name}: api reported last page")
                break

            request_state = page_result.next_request_state
            page_index += 1

        if expected_total is not None and len(collected_links) > expected_total:
            raise ValueError(
                f"{class_name}: collected more links than expected total "
                f"links={len(collected_links)} "
                f"expected_total={expected_total}"
            )

        return collected_links, expected_total

    def _get_max_attempts(self) -> int:
        return 1

    @abstractmethod
    def _get_initial_request_state(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def _fetch_listing_response(self, request_state: Any) -> Any:
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
        raise NotImplementedError

    def _get_request_state_key(self, request_state: Any) -> str:
        return repr(request_state)
