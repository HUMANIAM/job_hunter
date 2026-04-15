from __future__ import annotations

from typing import Any

from clients.sources.browser_listing_adapter import (
    AdvanceDecision,
    BrowserListingAdapter,
    PageAdvance,
)


SIOUX_ENTRY_URL = "https://vacancy.sioux.eu/"
SIOUX_RESULTS_READY_SELECTOR = "a.act-item-job-overview"
SIOUX_COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"


class SiouxBrowserListingAdapter(BrowserListingAdapter):
    """Typed placeholder for the Sioux browser-listing refactor."""

    entry_url = SIOUX_ENTRY_URL
    listing_label = "sioux listing"
    results_ready_selectors = (SIOUX_RESULTS_READY_SELECTOR,)
    cookie_accept_selectors = (SIOUX_COOKIE_ACCEPT_SELECTOR,)

    def _collect_job_links_in_context(
        self,
        context: Any,
        page: Any,
        *,
        job_limit: int,
    ) -> list[str]:
        return []

    def _get_job_links_from_page(
        self,
        page: Any,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return set()

    def _get_page_advance(self, page: Any) -> PageAdvance:
        return PageAdvance(advance_decision=AdvanceDecision.STOP)

    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        return page
