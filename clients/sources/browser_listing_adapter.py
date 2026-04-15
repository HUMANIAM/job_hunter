from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Sequence

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log


NEXT_PAGE_CONTROL_NOT_USABLE = "next page control not usable"


class AdvanceDecision(str, Enum):
    """How a browser listing should advance after processing the current page."""

    FOLLOW_URL = "follow_url"
    CLICK = "click"
    STOP = "stop"


@dataclass(frozen=True)
class PageAdvance:
    """The pagination instruction for the current browser listing page."""

    advance_decision: AdvanceDecision
    next_page_url: str | None = None


class BrowserListingAdapter(BaseClientAdapter, ABC):
    """Contract for client adapters that collect job links from browser DOM pages.

    This is a browser-listing-specific adapter contract, not the global public
    adapter protocol. External callers should still use `collect_job_links(...)`.

    Subclasses are expected to:
    - provide the entry-point configuration for the listing surface
    - extract only the links visible on the current page
    - decide how pagination should advance from the current page
    - return the next listing URL together with the advance decision when needed
    - resolve that page-advance instruction into the next page object
    """

    entry_url: str
    listing_label: str
    results_ready_selectors: Sequence[str]
    cookie_accept_selectors: Sequence[str] = ()

    def _open_page(self, page: Any, url: str) -> None:
        """Open a listing page and apply the shared browser-listing preparation."""

        clicked_selectors = open_and_prepare_page(
            page,
            url,
            wait_for=self.results_ready_selectors,
            click_if_visible_selectors=self.cookie_accept_selectors,
        )
        if clicked_selectors:
            log(f"accepted cookie banner selectors: {clicked_selectors}")

        log(f"current page url: {page.url}")

    def _collect_job_links_from_page_common(
        self,
        page: Any,
        *,
        log_context: str,
        job_limit: int,
        candidates_selector: str,
        found_label: str,
        normalize_href: Callable[[str], str | None],
        is_job_url: Callable[[str], bool],
    ) -> set[str]:
        """Collect deduplicated job URLs from DOM anchors on the current page."""

        hrefs: set[str] = set()

        links = page.locator(candidates_selector)
        count = links.count()
        log(f"{log_context}: found {count} {found_label}")

        for index in range(count):
            href = links.nth(index).get_attribute("href")
            if not href:
                continue

            full_url = normalize_href(href)
            if not full_url or not is_job_url(full_url):
                continue

            hrefs.add(full_url)
            if len(hrefs) >= job_limit:
                break

        log(f"{log_context}: collected {len(hrefs)} job links from current page")
        return hrefs

    def _get_page_advance_common(
        self,
        page: Any,
        *,
        next_selectors: Sequence[str],
        normalize_next_href: Callable[[str], str | None],
        is_click_next_control: Callable[[Any], bool],
    ) -> PageAdvance:
        """Detect whether pagination should follow a URL, click, or stop."""

        for selector in next_selectors:
            try:
                element = page.locator(selector).first
                if element.count() == 0:
                    continue

                href = element.get_attribute("href")
                if href:
                    next_page_url = normalize_next_href(href)
                    if next_page_url:
                        return PageAdvance(
                            advance_decision=AdvanceDecision.FOLLOW_URL,
                            next_page_url=next_page_url,
                        )

                if is_click_next_control(element):
                    return PageAdvance(advance_decision=AdvanceDecision.CLICK)
            except Exception as exc:
                log(
                    f"next page detection: selector '{selector}' raised "
                    f"{exc.__class__.__name__}: {exc}"
                )

        return PageAdvance(advance_decision=AdvanceDecision.STOP)

    def _get_next_page_common(
        self,
        page: Any,
        page_advance: PageAdvance,
        *,
        click_next_page: Callable[[Any], bool] | None = None,
    ) -> Any:
        """Execute the page advance instruction and return the active page."""

        if page_advance.advance_decision == AdvanceDecision.FOLLOW_URL:
            if not page_advance.next_page_url:
                raise ValueError("FOLLOW_URL requires next_page_url")

            self._open_page(page, page_advance.next_page_url)
            return page

        if page_advance.advance_decision == AdvanceDecision.CLICK:
            if click_next_page is None:
                raise ValueError("CLICK requires click_next_page")
            if not click_next_page(page):
                raise RuntimeError(NEXT_PAGE_CONTROL_NOT_USABLE)
            return page

        raise ValueError("STOP cannot be executed as a next page advance")

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        expected_count: int | None = None,
        *,
        job_limit: int,
    ) -> set[str]:
        """Traverse paginated browser listings until stop conditions are met."""

        collected_links: set[str] = set()
        visited_pages: set[str] = set()
        page_index = 1

        while True:
            current_url = page.url
            if current_url in visited_pages:
                log(f"{context}: detected repeated page url, skipping")
            else:
                visited_pages.add(current_url)

                if len(collected_links) >= job_limit:
                    log(f"{context}: reached job limit, stopping pagination")
                    break

                page_links = self._get_job_links_from_page(
                    page,
                    f"{context} page {page_index}",
                    job_limit=job_limit - len(collected_links),
                )
                before = len(collected_links)
                collected_links.update(page_links)
                after = len(collected_links)

                log(
                    f"{context} page {page_index}: "
                    f"added {after - before} new links | cumulative={after}"
                )

                if expected_count is not None and expected_count > 0 and after >= expected_count:
                    log(f"{context}: reached expected count, stopping pagination")
                    break

                if len(collected_links) >= job_limit:
                    log(f"{context}: reached job limit, stopping pagination")
                    break

            page_advance = self._get_page_advance(page)
            if page_advance.advance_decision == AdvanceDecision.STOP:
                log(f"{context}: no next page link")
                break

            if (
                page_advance.advance_decision == AdvanceDecision.FOLLOW_URL
                and page_advance.next_page_url in visited_pages
            ):
                log(f"{context}: next page url already visited, stopping")
                break

            if page_advance.advance_decision == AdvanceDecision.FOLLOW_URL:
                log(f"{context}: following next page -> {page_advance.next_page_url}")
            elif page_advance.advance_decision == AdvanceDecision.CLICK:
                log(f"{context}: clicking next page")

            try:
                page = self._get_next_page(page, page_advance)
            except RuntimeError as exc:
                if str(exc) != NEXT_PAGE_CONTROL_NOT_USABLE:
                    raise

                log(f"{context}: {NEXT_PAGE_CONTROL_NOT_USABLE}")
                break
            page_index += 1

        return collected_links

    @abstractmethod
    def _get_job_links_from_page(
        self,
        page: Any,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        """Return only the job links visible on the current listing page."""
        raise NotImplementedError

    @abstractmethod
    def _get_page_advance(self, page: Any) -> PageAdvance:
        """Return the next pagination instruction for the current browser page.

        When `advance_decision` is `FOLLOW_URL`, `next_page_url` should contain
        the next listing URL. For `CLICK` and `STOP`, `next_page_url` should
        usually be `None`.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        """Execute the page-advance instruction and return the next page object.

        Implementations should interpret `page_advance.advance_decision` and
        either navigate to `page_advance.next_page_url`, click the relevant next
        control, or reject invalid `STOP` inputs. The returned object is the
        page instance positioned on the next listing page.
        """
        raise NotImplementedError
